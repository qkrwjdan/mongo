/**
 *    Copyright (C) 2022-present MongoDB, Inc.
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the Server Side Public License, version 1,
 *    as published by MongoDB, Inc.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    Server Side Public License for more details.
 *
 *    You should have received a copy of the Server Side Public License
 *    along with this program. If not, see
 *    <http://www.mongodb.com/licensing/server-side-public-license>.
 *
 *    As a special exception, the copyright holders give permission to link the
 *    code of portions of this program with the OpenSSL library under certain
 *    conditions as described in each individual source file and distribute
 *    linked combinations including the program with the OpenSSL library. You
 *    must comply with the Server Side Public License in all respects for
 *    all of the code used other than as permitted herein. If you modify file(s)
 *    with this exception, you may extend this exception to your version of the
 *    file(s), but you are not obligated to do so. If you do not wish to do so,
 *    delete this exception statement from your version. If you delete this
 *    exception statement from all source files in the program, then also delete
 *    it in the license file.
 */

#pragma once

#include <vector>

#include "mongo/bson/util/bson_extract.h"
#include "mongo/db/auth/authorization_session.h"
#include "mongo/db/auth/validated_tenancy_scope.h"
#include "mongo/db/commands.h"
#include "mongo/db/fle_crud.h"
#include "mongo/db/query/count_command_as_aggregation_command.h"
#include "mongo/db/query/count_command_gen.h"
#include "mongo/db/query/query_stats/count_key.h"
#include "mongo/db/query/query_stats/query_stats.h"
#include "mongo/db/query/view_response_formatter.h"
#include "mongo/db/views/resolved_view.h"
#include "mongo/platform/overflow_arithmetic.h"
#include "mongo/rpc/get_status_from_command_result.h"
#include "mongo/s/catalog_cache.h"
#include "mongo/s/cluster_commands_helpers.h"
#include "mongo/s/commands/query_cmd/cluster_explain.h"
#include "mongo/s/commands/strategy.h"
#include "mongo/s/grid.h"
#include "mongo/s/query/exec/cluster_cursor_manager.h"
#include "mongo/s/query/planner/cluster_aggregate.h"
#include "mongo/util/assert_util.h"
#include "mongo/util/timer.h"

namespace mongo {

namespace {

// The # of documents returned is always 1 for the count command.
static constexpr long long kNReturned = 1;

}  // namespace

/**
 * Implements the find command on mongos.
 */
template <typename Impl>
class ClusterCountCmdBase final : public ErrmsgCommandDeprecated {
public:
    ClusterCountCmdBase() : ErrmsgCommandDeprecated(Impl::kName) {}

    const std::set<std::string>& apiVersions() const override {
        return Impl::getApiVersions();
    }

    AllowedOnSecondary secondaryAllowed(ServiceContext*) const override {
        return AllowedOnSecondary::kAlways;
    }

    bool adminOnly() const override {
        return false;
    }

    ReadWriteType getReadWriteType() const override {
        return ReadWriteType::kRead;
    }

    bool supportsWriteConcern(const BSONObj& cmd) const override {
        return false;
    }

    ReadConcernSupportResult supportsReadConcern(const BSONObj& cmdObj,
                                                 repl::ReadConcernLevel level,
                                                 bool isImplicitDefault) const override {
        static const Status kSnapshotNotSupported{ErrorCodes::InvalidOptions,
                                                  "read concern snapshot not supported"};
        return {{level == repl::ReadConcernLevel::kSnapshotReadConcern, kSnapshotNotSupported},
                Status::OK()};
    }

    Status checkAuthForOperation(OperationContext* opCtx,
                                 const DatabaseName& dbName,
                                 const BSONObj& cmdObj) const override {
        auto* as = AuthorizationSession::get(opCtx->getClient());
        if (!as->isAuthorizedForActionsOnResource(parseResourcePattern(dbName, cmdObj),
                                                  ActionType::find)) {
            return {ErrorCodes::Unauthorized, "unauthorized"};
        }

        return Impl::checkAuthForOperation(opCtx, dbName, cmdObj);
    }

    bool errmsgRun(OperationContext* opCtx,
                   const DatabaseName& dbName,
                   const BSONObj& cmdObj,
                   std::string& errmsg,
                   BSONObjBuilder& result) override {
        Impl::checkCanRunHere(opCtx);

        CommandHelpers::handleMarkKillOnClientDisconnect(opCtx);
        const NamespaceString nss(parseNs(dbName, cmdObj));
        uassert(ErrorCodes::InvalidNamespace,
                str::stream() << "Invalid namespace specified '" << nss.toStringForErrorMsg()
                              << "'",
                nss.isValid());

        std::vector<AsyncRequestsSender::Response> shardResponses;
        try {
            auto countRequest = CountCommandRequest::parse(IDLParserContext("count"), cmdObj);
            if (shouldDoFLERewrite(countRequest)) {
                if (!countRequest.getEncryptionInformation()->getCrudProcessed().value_or(false)) {
                    processFLECountS(opCtx, nss, &countRequest);
                }
                stdx::lock_guard<Client> lk(*opCtx->getClient());
                CurOp::get(opCtx)->setShouldOmitDiagnosticInformation_inlock(lk, true);
            }

            const auto cri = uassertStatusOK(
                Grid::get(opCtx)->catalogCache()->getCollectionRoutingInfo(opCtx, nss));
            const auto collation = countRequest.getCollation().get_value_or(BSONObj());

            const auto expCtx =
                makeExpressionContextWithDefaultsForTargeter(opCtx,
                                                             nss,
                                                             cri,
                                                             collation,
                                                             boost::none /*explainVerbosity*/,
                                                             boost::none /*letParameters*/,
                                                             boost::none /*runtimeConstants*/);

            const auto parsedFind = uassertStatusOK(parsed_find_command::parseFromCount(
                expCtx, countRequest, ExtensionsCallbackNoop(), nss));

            if (feature_flags::gFeatureFlagQueryStatsCountDistinct.isEnabled(
                    serverGlobalParams.featureCompatibility.acquireFCVSnapshot())) {
                query_stats::registerRequest(opCtx, nss, [&]() {
                    return std::make_unique<query_stats::CountKey>(
                        expCtx,
                        *parsedFind,
                        countRequest.getLimit().has_value(),
                        countRequest.getSkip().has_value(),
                        countRequest.getReadConcern(),
                        countRequest.getMaxTimeMS().has_value());
                });
            }

            // We only need to factor in the skip value when sending to the shards if we
            // have a value for limit, otherwise, we apply it only once we have collected all
            // counts.
            if (countRequest.getLimit() && countRequest.getSkip()) {
                const auto limit = countRequest.getLimit().value();
                const auto skip = countRequest.getSkip().value();
                if (limit != 0) {
                    std::int64_t sum = 0;
                    uassert(ErrorCodes::Overflow,
                            str::stream()
                                << "Overflow on the count command: The sum of the limit and skip "
                                   "fields must fit into a long integer. Limit: "
                                << limit << "   Skip: " << skip,
                            !overflow::add(limit, skip, &sum));
                    countRequest.setLimit(sum);
                }
            }
            countRequest.setSkip(boost::none);

            shardResponses = scatterGatherVersionedTargetByRoutingTable(
                expCtx,
                dbName,
                nss,
                cri,
                applyReadWriteConcern(
                    opCtx,
                    this,
                    CommandHelpers::filterCommandRequestForPassthrough(countRequest.toBSON())),
                ReadPreferenceSetting::get(opCtx),
                Shard::RetryPolicy::kIdempotent,
                countRequest.getQuery(),
                collation,
                true /*eligibleForSampling*/);
        } catch (const ExceptionFor<ErrorCodes::CommandOnShardedViewNotSupportedOnMongod>& ex) {
            // Rewrite the count command as an aggregation.
            auto countRequest = CountCommandRequest::parse(IDLParserContext("count"), cmdObj);
            auto aggCmdOnView =
                uassertStatusOK(countCommandAsAggregationCommand(countRequest, nss));
            const boost::optional<auth::ValidatedTenancyScope>& vts =
                auth::ValidatedTenancyScope::get(opCtx);
            auto aggCmdOnViewObj = OpMsgRequestBuilder::create(vts, dbName, aggCmdOnView).body;
            auto aggRequestOnView =
                aggregation_request_helper::parseFromBSON(aggCmdOnViewObj, vts, boost::none);

            auto resolvedAggRequest = ex->asExpandedViewAggregation(aggRequestOnView);
            auto resolvedAggCmd =
                aggregation_request_helper::serializeToCommandObj(resolvedAggRequest);

            BSONObj aggResult = CommandHelpers::runCommandDirectly(
                opCtx,
                OpMsgRequestBuilder::create(
                    auth::ValidatedTenancyScope::get(opCtx), dbName, std::move(resolvedAggCmd)));

            result.resetToEmpty();
            ViewResponseFormatter formatter(aggResult);
            auto formatStatus = formatter.appendAsCountResponse(&result, boost::none);
            uassertStatusOK(formatStatus);

            return true;
        } catch (const ExceptionFor<ErrorCodes::NamespaceNotFound>&) {
            // If there's no collection with this name, the count aggregation behavior below
            // will produce a total count of 0.
            shardResponses = {};
        }

        long long total = 0;
        BSONObjBuilder shardSubTotal(result.subobjStart("shards"));

        for (const auto& response : shardResponses) {
            auto status = response.swResponse.getStatus();
            if (status.isOK()) {
                status = getStatusFromCommandResult(response.swResponse.getValue().data);
                if (status.isOK()) {
                    long long shardCount = response.swResponse.getValue().data["n"].numberLong();
                    shardSubTotal.appendNumber(response.shardId.toString(), shardCount);
                    total += shardCount;
                    continue;
                }
            }

            shardSubTotal.doneFast();
            // Add error context so that you can see on which shard failed as well as details
            // about that error.
            uassertStatusOK(status.withContext(str::stream() << "failed on: " << response.shardId));
        }

        shardSubTotal.doneFast();
        total = applySkipLimit(total, cmdObj);
        result.appendNumber("n", total);

        auto* curOp = CurOp::get(opCtx);
        curOp->setEndOfOpMetrics(kNReturned);

        collectQueryStatsMongos(opCtx, std::move(curOp->debug().queryStatsInfo.key));

        return true;
    }

    Status explain(OperationContext* opCtx,
                   const OpMsgRequest& request,
                   ExplainOptions::Verbosity verbosity,
                   rpc::ReplyBuilderInterface* result) const override {
        Impl::checkCanExplainHere(opCtx);

        const BSONObj& cmdObj = request.body;

        CountCommandRequest countRequest(NamespaceStringOrUUID(NamespaceString{}));
        try {
            countRequest = CountCommandRequest::parse(IDLParserContext("count"), request);
        } catch (...) {
            return exceptionToStatus();
        }

        const NamespaceString nss = parseNs(countRequest.getDbName(), cmdObj);
        uassert(ErrorCodes::InvalidNamespace,
                str::stream() << "Invalid namespace specified '" << nss.toStringForErrorMsg()
                              << "'",
                nss.isValid());

        // If the command has encryptionInformation, rewrite the query as necessary.
        if (shouldDoFLERewrite(countRequest)) {
            processFLECountS(opCtx, nss, &countRequest);

            stdx::lock_guard<Client> lk(*opCtx->getClient());
            CurOp::get(opCtx)->setShouldOmitDiagnosticInformation_inlock(lk, true);
        }

        BSONObj targetingQuery = countRequest.getQuery();
        BSONObj targetingCollation = countRequest.getCollation().value_or(BSONObj());

        const auto explainCmd = ClusterExplain::wrapAsExplain(countRequest.toBSON(), verbosity);

        // We will time how long it takes to run the commands on the shards
        Timer timer;

        std::vector<AsyncRequestsSender::Response> shardResponses;
        try {
            const auto cri = uassertStatusOK(
                Grid::get(opCtx)->catalogCache()->getCollectionRoutingInfo(opCtx, nss));
            shardResponses =
                scatterGatherVersionedTargetByRoutingTable(opCtx,
                                                           nss.dbName(),
                                                           nss,
                                                           cri,
                                                           explainCmd,
                                                           ReadPreferenceSetting::get(opCtx),
                                                           Shard::RetryPolicy::kIdempotent,
                                                           targetingQuery,
                                                           targetingCollation,
                                                           boost::none /*letParameters*/,
                                                           boost::none /*runtimeConstants*/);
        } catch (const ExceptionFor<ErrorCodes::CommandOnShardedViewNotSupportedOnMongod>& ex) {
            CountCommandRequest countRequest(NamespaceStringOrUUID(NamespaceString{}));
            try {
                countRequest = CountCommandRequest::parse(IDLParserContext("count"), cmdObj);
            } catch (...) {
                return exceptionToStatus();
            }

            auto aggCmdOnView = countCommandAsAggregationCommand(countRequest, nss);
            if (!aggCmdOnView.isOK()) {
                return aggCmdOnView.getStatus();
            }

            const boost::optional<auth::ValidatedTenancyScope>& vts =
                auth::ValidatedTenancyScope::get(opCtx);
            auto aggCmdOnViewObj =
                OpMsgRequestBuilder::create(vts, nss.dbName(), aggCmdOnView.getValue()).body;
            auto aggRequestOnView =
                aggregation_request_helper::parseFromBSON(aggCmdOnViewObj, vts, verbosity);

            auto bodyBuilder = result->getBodyBuilder();
            // An empty PrivilegeVector is acceptable because these privileges are only checked
            // on getMore and explain will not open a cursor.
            return ClusterAggregate::retryOnViewError(opCtx,
                                                      aggRequestOnView,
                                                      *ex.extraInfo<ResolvedView>(),
                                                      nss,
                                                      PrivilegeVector(),
                                                      &bodyBuilder);
        }

        long long millisElapsed = timer.millis();

        const char* mongosStageName =
            ClusterExplain::getStageNameForReadOp(shardResponses.size(), cmdObj);

        auto bodyBuilder = result->getBodyBuilder();
        return ClusterExplain::buildExplainResult(
            ExpressionContext::makeBlankExpressionContext(opCtx, nss),
            shardResponses,
            mongosStageName,
            millisElapsed,
            cmdObj,
            &bodyBuilder);
    }

private:
    static long long applySkipLimit(long long num, const BSONObj& cmd) {
        BSONElement s = cmd["skip"];
        BSONElement l = cmd["limit"];

        if (s.isNumber()) {
            num = num - s.safeNumberLong();
            if (num < 0) {
                num = 0;
            }
        }

        if (l.isNumber()) {
            auto limit = l.safeNumberLong();
            if (limit < 0) {
                limit = -limit;
            }

            // 0 limit means no limit
            if (limit < num && limit != 0) {
                num = limit;
            }
        }

        return num;
    }
};

}  // namespace mongo

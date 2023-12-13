/**
 *    Copyright (C) 2018-present MongoDB, Inc.
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


// IWYU pragma: no_include "ext/alloc_traits.h"
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "mongo/base/error_codes.h"
#include "mongo/base/status.h"
#include "mongo/base/status_with.h"
#include "mongo/config.h"  // IWYU pragma: keep
#include "mongo/db/server_options.h"
#include "mongo/db/server_options_server_helpers.h"
#include "mongo/logv2/log.h"
#include "mongo/logv2/log_attr.h"
#include "mongo/logv2/log_component.h"
#include "mongo/logv2/log_component_settings.h"
#include "mongo/logv2/log_manager.h"
#include "mongo/logv2/log_severity.h"
#include "mongo/s/mongos_options.h"
#include "mongo/s/version_mongos.h"
#include "mongo/util/net/hostandport.h"
#include "mongo/util/net/socket_utils.h"
#include "mongo/util/options_parser/startup_options.h"
#include "mongo/util/str.h"

#define MONGO_LOGV2_DEFAULT_COMPONENT ::mongo::logv2::LogComponent::kSharding


namespace mongo {

MongosGlobalParams mongosGlobalParams;

void printMongosHelp(const moe::OptionSection& options) {
    std::cout << options.helpString() << std::endl;
};

bool handlePreValidationMongosOptions(const moe::Environment& params,
                                      const std::vector<std::string>& args) {
    if (params.count("help") && params["help"].as<bool>() == true) {
        printMongosHelp(moe::startupOptions);
        return false;
    }
    if (params.count("version") && params["version"].as<bool>() == true) {
        logMongosVersionInfo(&std::cout);
        return false;
    }
    if (params.count("test") && params["test"].as<bool>() == true) {
        logv2::LogManager::global().getGlobalSettings().setMinimumLoggedSeverity(
            mongo::logv2::LogComponent::kDefault, ::mongo::logv2::LogSeverity::Debug(5));
        return false;
    }

    return true;
}

Status validateMongosOptions(const moe::Environment& params) {
    Status ret = validateServerOptions(params);
    if (!ret.isOK()) {
        return ret;
    }

    return Status::OK();
}

Status canonicalizeMongosOptions(moe::Environment* params) {
    Status ret = canonicalizeServerOptions(params);
    if (!ret.isOK()) {
        return ret;
    }

    // "security.javascriptEnabled" comes from the config file, so override it if "noscripting"
    // is set since that comes from the command line.
    if (params->count("noscripting")) {
        auto status = params->set("security.javascriptEnabled",
                                  moe::Value(!(*params)["noscripting"].as<bool>()));
        if (!status.isOK()) {
            return status;
        }

        status = params->remove("noscripting");
        if (!status.isOK()) {
            return status;
        }
    }

    return Status::OK();
}

Status storeMongosOptions(const moe::Environment& params) {
    Status ret = storeServerOptions(params);
    if (!ret.isOK()) {
        return ret;
    }

    if (params.count("security.javascriptEnabled")) {
        mongosGlobalParams.scriptingEnabled = params["security.javascriptEnabled"].as<bool>();
    }

    if (!params.count("sharding.configDB")) {
        return Status(ErrorCodes::BadValue, "error: no args for --configdb");
    }

    mongosGlobalParams.upgradeBackCompat = params.count("upgradeBackCompat");
    mongosGlobalParams.downgradeBackCompat = params.count("downgradeBackCompat");

    return Status::OK();
}

}  // namespace mongo

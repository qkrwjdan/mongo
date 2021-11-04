/**
 * Tests that the "shard merge" protocol is enabled only in the proper FCV.
 * @tags: [requires_fcv_51, featureFlagShardMerge]
 */

(function() {
"use strict";

load("jstests/replsets/libs/tenant_migration_util.js");

function runTest(downgradeFCV) {
    let rst = new ReplSetTest({nodes: 1});
    rst.startSet();
    rst.initiate();

    let primary = rst.getPrimary();
    let adminDB = primary.getDB("admin");
    const kDummyConnStr = "mongodb://localhost/?replicaSet=foo";
    // A function, not a constant, to ensure unique UUIDs.
    function donorStartMigrationCmd() {
        return {
            donorStartMigration: 1,
            protocol: "shard merge",
            tenantId: "foo",
            migrationId: UUID(),
            recipientConnectionString: kDummyConnStr,
            readPreference: {mode: "primary"},
        };
    }

    // Preconditions: the shard merge feature is enabled and our fresh RS is on the latest FCV.
    assert(TenantMigrationUtil.isShardMergeEnabled(adminDB));
    assert.eq(getFCVConstants().latest,
              adminDB.system.version.findOne({_id: 'featureCompatibilityVersion'}).version);

    // Shard merge is enabled, so this call will fail for some *other* reason, e.g. no certificates,
    // recipient is unavailable.
    let res = adminDB.runCommand(donorStartMigrationCmd());
    assert.neq(res.code,
               5949300,
               "donorStartMigration shouldn't reject 'shard merge' protocol when it's enabled");

    assert.commandWorked(adminDB.adminCommand({setFeatureCompatibilityVersion: downgradeFCV}));

    // Now that FCV is downgraded, shard merge is automatically disabled.
    assert.commandFailedWithCode(
        adminDB.runCommand(donorStartMigrationCmd()),
        5949300,
        "donorStartMigration should reject 'shard merge' protocol when it's disabled");

    rst.stopSet();
}

runFeatureFlagMultiversionTest('featureFlagShardMerge', runTest);
})();

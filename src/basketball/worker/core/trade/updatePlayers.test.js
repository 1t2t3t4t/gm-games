// @flow

import assert from "assert";
import { afterEach, before, describe, it } from "mocha";
import { trade } from "..";
import { idb } from "../../../../deion/worker/db";
import { g } from "../../../../deion/worker/util";
import { beforeTests, reset } from "./common.test";

describe("worker/core/trade/updatePlayers", () => {
    before(beforeTests);
    afterEach(reset);

    it("allow players from both teams to be set", async () => {
        await trade.create([
            {
                tid: g.userTid,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 1,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        const userPidsTest = [0, 1];
        const otherPidsTest = [2, 3];
        const teams = await trade.updatePlayers([
            {
                tid: g.userTid,
                pids: userPidsTest,
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 1,
                pids: otherPidsTest,
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        assert.deepEqual(teams[0].pids, userPidsTest);
        assert.deepEqual(teams[1].pids, otherPidsTest);
    });

    it("filter out invalid players", async () => {
        await trade.create([
            {
                tid: g.userTid,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 1,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        const teams = await trade.updatePlayers([
            {
                tid: g.userTid,
                pids: [1, 16, 20, 48, 50, 90],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 1,
                pids: [12, 63, 3, 87, 97, 524],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        assert.deepEqual(teams[0].pids, [1]);
        assert.deepEqual(teams[1].pids, [3]);
    });

    it("delete the other team's players, but not the user's players, from the trade when a new team is selected", async () => {
        await trade.create([
            {
                tid: g.userTid,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 1,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        const userPidsTest = [0, 1];
        const otherPidsTest = [2, 3];
        let teams = await trade.updatePlayers([
            {
                tid: g.userTid,
                pids: userPidsTest,
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 1,
                pids: otherPidsTest,
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        assert.deepEqual(teams[0].pids, userPidsTest);
        assert.deepEqual(teams[1].pids, otherPidsTest);

        await trade.create([
            {
                tid: g.userTid,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
            {
                tid: 2,
                pids: [],
                pidsExcluded: [],
                dpids: [],
                dpidsExcluded: [],
            },
        ]);
        const tr = await idb.cache.trade.get(0);
        teams = tr.teams;
        assert.deepEqual(teams[0].pids, userPidsTest);
        assert.deepEqual(teams[1].pids, []);
    });
});

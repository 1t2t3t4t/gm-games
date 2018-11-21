// @flow

import { player } from "../core";
import { idb } from "../../../deion/worker/db";
import { g } from "../../../deion/worker/util";

async function updateUpcomingFreeAgents(inputs: {
    season: number,
}): void | { [key: string]: any } {
    const stats = ["min", "pts", "trb", "ast", "per"];

    let players: any[] = await idb.getCopies.players({
        tid: [0, Infinity],
        filter: p => p.contract.exp === inputs.season,
    });

    // Done before filter so full player object can be passed to player.genContract.
    for (let i = 0; i < players.length; i++) {
        players[i].contractDesired = player.genContract(
            players[i],
            false,
            false,
        ); // No randomization
        players[i].contractDesired.amount /= 1000;
        players[i].contractDesired.exp += inputs.season - g.season;
    }

    players = await idb.getCopies.playersPlus(players, {
        attrs: [
            "pid",
            "name",
            "abbrev",
            "age",
            "contract",
            "freeAgentMood",
            "injury",
            "contractDesired",
            "watch",
        ],
        ratings: ["ovr", "pot", "skills", "pos"],
        stats,
        season: g.season,
        showNoStats: true,
        showRookies: true,
        fuzz: true,
    });

    return {
        players,
        season: inputs.season,
        stats,
    };
}

export default {
    runBefore: [updateUpcomingFreeAgents],
};

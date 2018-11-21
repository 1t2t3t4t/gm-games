// @flow

import { PHASE } from "../../../deion/common";
import { idb } from "../../../deion/worker/db";
import { g } from "../../../deion/worker/util";
import type { GetOutput, UpdateEvents } from "../../../deion/common/types";

async function updateHistory(
    inputs: GetOutput,
    updateEvents: UpdateEvents,
): void | { [key: string]: any } {
    if (
        updateEvents.includes("firstRun") ||
        (updateEvents.includes("newPhase") && g.phase === PHASE.DRAFT_LOTTERY)
    ) {
        const [awards, teams] = await Promise.all([
            idb.getCopies.awards(),
            idb.getCopies.teamsPlus({
                attrs: ["tid", "abbrev", "region", "name"],
                seasonAttrs: ["season", "playoffRoundsWon", "won", "lost"],
            }),
        ]);

        const awardNames = ["finalsMvp", "mvp", "dpoy", "smoy", "mip", "roy"];

        const seasons = awards.map(a => {
            return {
                season: a.season,
                finalsMvp: a.finalsMvp,
                mvp: a.mvp,
                dpoy: a.dpoy,
                smoy: a.smoy,
                mip: a.mip,
                roy: a.roy,
                runnerUp: undefined,
                champ: undefined,
            };
        });

        for (const t of teams) {
            // t.seasonAttrs has same season entries as the "seasons" array built from awards
            for (let i = 0; i < seasons.length; i++) {
                // Find corresponding entries in seasons and t.seasonAttrs. Can't assume they are the same because they aren't if some data has been deleted (Delete Old Data)
                let found = false;
                let j;
                for (j = 0; j < t.seasonAttrs.length; j++) {
                    if (t.seasonAttrs[j].season === seasons[i].season) {
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    continue;
                }

                if (
                    t.seasonAttrs[j].playoffRoundsWon ===
                    g.numGamesPlayoffSeries.length
                ) {
                    seasons[i].champ = {
                        tid: t.tid,
                        abbrev: t.abbrev,
                        region: t.region,
                        name: t.name,
                        won: t.seasonAttrs[j].won,
                        lost: t.seasonAttrs[j].lost,
                        count: 0,
                    };
                } else if (
                    t.seasonAttrs[j].playoffRoundsWon ===
                    g.numGamesPlayoffSeries.length - 1
                ) {
                    seasons[i].runnerUp = {
                        tid: t.tid,
                        abbrev: t.abbrev,
                        region: t.region,
                        name: t.name,
                        won: t.seasonAttrs[j].won,
                        lost: t.seasonAttrs[j].lost,
                    };
                }
            }
        }

        // Count up number of championships per team
        const championshipsByTid = [];
        for (let i = 0; i < g.numTeams; i++) {
            championshipsByTid.push(0);
        }
        for (let i = 0; i < seasons.length; i++) {
            if (seasons[i].champ) {
                championshipsByTid[seasons[i].champ.tid] += 1;
                seasons[i].champ.count =
                    championshipsByTid[seasons[i].champ.tid];
            }
        }

        return {
            awards: awardNames,
            seasons,
            teamAbbrevsCache: g.teamAbbrevsCache,
            userTid: g.userTid,
        };
    }
}

export default {
    runBefore: [updateHistory],
};

import React, { useState } from "react";
import { SafeHtml } from "../components";
import useTitleBar from "../hooks/useTitleBar";
import type { View, LogEventType } from "../../common/types";
import { helpers } from "../util";
import classNames from "classnames";

const categories = {
	award: {
		text: "Awards",
		className: "badge-warning",
	},
	draft: {
		text: "Draft",
		className: "badge-primary",
	},
	league: {
		text: "League",
		className: "badge-secondary",
	},
	injury: {
		text: "Injuries",
		className: "badge-danger",
	},
	playerFeat: {
		text: "Player Feats",
		className: "badge-success",
	},
	playoffs: {
		text: "Playoffs",
		className: "badge-primary",
	},
	rare: {
		text: "Rare Events",
		className: "badge-dark",
	},
	transaction: {
		text: "Transactions",
		className: "badge-info",
	},
	team: {
		text: "Teams",
		className: "badge-light",
	},
};

const types: Partial<Record<
	LogEventType,
	{
		text: string;
		category: keyof typeof categories;
	}
>> = {
	injured: {
		text: "Injury",
		category: "injury",
	},
	healed: {
		text: "Recovery",
		category: "injury",
	},
	playerFeat: {
		text: "Player Feat",
		category: "playerFeat",
	},
	playoffs: {
		text: "Playoffs",
		category: "playoffs",
	},
	madePlayoffs: {
		text: "Playoffs",
		category: "playoffs",
	},
	freeAgent: {
		text: "Free Agent",
		category: "transaction",
	},
	reSigned: {
		text: "Re-signing",
		category: "transaction",
	},
	release: {
		text: "Released",
		category: "transaction",
	},
	retired: {
		text: "Retirement",
		category: "transaction",
	},
	trade: {
		text: "Trade",
		category: "transaction",
	},
	award: {
		text: "Award",
		category: "award",
	},
	hallOfFame: {
		text: "Hall of Fame",
		category: "award",
	},
	ageFraud: {
		text: "Fraud",
		category: "rare",
	},
	tragedy: {
		text: "Tragic Death",
		category: "rare",
	},
	teamContraction: {
		text: "Contraction",
		category: "team",
	},
	teamExpansion: {
		text: "Expansion",
		category: "team",
	},
	teamLogo: {
		text: "New Logo",
		category: "team",
	},
	teamRelocation: {
		text: "Relocation",
		category: "team",
	},
	teamRename: {
		text: "Rename",
		category: "team",
	},
	gameAttribute: {
		text: "League",
		category: "league",
	},
	draft: {
		text: "Draft",
		category: "draft",
	},
	draftLottery: {
		text: "Draft Lottery",
		category: "draft",
	},
};

const Badge = ({ type }: { type: LogEventType }) => {
	let text;
	let className;
	const typeInfo = types[type];
	if (typeInfo) {
		text = typeInfo.text;
		className = categories[typeInfo.category].className;
	} else {
		text = type;
		className = "badge-secondary";
	}
	return (
		<span className={`badge badge-news ml-auto align-self-start ${className}`}>
			{text}
		</span>
	);
};

const News = ({
	abbrev,
	events,
	level,
	order,
	season,
	teams,
	userTid,
}: View<"news">) => {
	const [showCategories, setShowCategories] = useState<
		Record<keyof typeof categories, boolean>
	>({
		award: true,
		draft: true,
		injury: true,
		league: true,
		playerFeat: true,
		playoffs: true,
		rare: true,
		transaction: true,
		team: true,
	});

	useTitleBar({
		title: "News Feed",
		dropdownView: "news",
		dropdownFields: {
			seasons: season,
			newsLevels: level,
			teamsAndAll: abbrev,
			newestOldestFirst: order,
		},
	});

	return (
		<>
			<div className="mt-1" style={{ marginLeft: "-0.5rem" }}>
				{helpers.keys(categories).map(category => {
					const info = categories[category];
					return (
						<div
							key={category}
							className={classNames(
								"form-check form-check-inline mb-2 ml-2",
								{},
							)}
						>
							<input
								className="form-check-input"
								type="checkbox"
								checked={showCategories[category]}
								id={`news-${category}`}
								onChange={() => {
									setShowCategories(show => ({
										...show,
										[category]: !show[category],
									}));
								}}
							/>
							<label
								className={`form-check-label badge badge-news ${info.className}`}
								htmlFor={`news-${category}`}
							>
								{info.text}
							</label>
						</div>
					);
				})}
			</div>

			<div className="mb-3">
				<button
					className="btn btn-link p-0"
					onClick={event => {
						event.preventDefault();
						const show = { ...showCategories };
						for (const key of helpers.keys(show)) {
							show[key] = true;
						}
						setShowCategories(show);
					}}
				>
					All
				</button>{" "}
				|{" "}
				<button
					className="btn btn-link p-0"
					onClick={event => {
						event.preventDefault();
						const show = { ...showCategories };
						for (const key of helpers.keys(show)) {
							show[key] = false;
						}
						setShowCategories(show);
					}}
				>
					None
				</button>
			</div>

			<div className="row">
				{events
					.filter(event => {
						const type = types[event.type];
						if (type) {
							return showCategories[type.category] === true;
						}
						return true;
					})
					.map(event => {
						const teamInfo =
							event.tid !== undefined
								? teams.find(t => t.tid === event.tid)
								: undefined;

						return (
							<div
								key={event.eid}
								className="col-lg-3 col-md-4 col-sm-6 col-12"
							>
								<div className="card mb-3">
									<div
										className={classNames(
											"p-2 d-flex",
											event.tids && event.tids.includes(userTid)
												? "table-info"
												: "card-header",
										)}
									>
										{teamInfo ? (
											<a
												href={helpers.leagueUrl([
													"roster",
													`${teamInfo.seasonAttrs.abbrev}_${event.tid}`,
												])}
											>
												{teamInfo.seasonAttrs.region}{" "}
												{teamInfo.seasonAttrs.name}
											</a>
										) : null}
										<Badge type={event.type} />
									</div>
									<div className="p-2">
										<SafeHtml dirty={event.text} />
										{event.score !== undefined ? (
											<div className="text-muted">Score: {event.score}</div>
										) : null}
									</div>
								</div>
							</div>
						);
					})}
			</div>
		</>
	);
};

export default News;

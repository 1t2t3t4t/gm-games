import classNames from "classnames";
import { groupBy } from "../../common/groupBy";
import PropTypes from "prop-types";
import { Fragment, useEffect, useState } from "react";
import type { MouseEvent, ReactNode } from "react";
import {
	ACCOUNT_API_URL,
	STRIPE_PUBLISHABLE_KEY,
	fetchWrapper,
	GAME_NAME,
} from "../../common";
import useTitleBar from "../hooks/useTitleBar";
import { confirm, getScript, localActions, realtimeUpdate } from "../util";
import type { View } from "../../common/types";
import { GameLinks } from "../components";
import { ajaxErrorMsg } from "./LoginOrRegister";

const StripeButton = ({ email }: { email: string }) => {
	const [handler, setHandler] = useState<StripeCheckoutHandler | undefined>();

	useEffect(() => {
		(async () => {
			if (!window.StripeCheckout) {
				await getScript("https://checkout.stripe.com/checkout.js");
			}

			setHandler(
				window.StripeCheckout.configure({
					key: STRIPE_PUBLISHABLE_KEY,
					image: "/ico/icon128.png",
					token: async token => {
						try {
							const data = await fetchWrapper({
								url: `${ACCOUNT_API_URL}/gold_start.php`,
								method: "POST",
								data: {
									sport: process.env.SPORT,
									token: token.id,
								},
								credentials: "include",
							});
							realtimeUpdate(["account"], "/account", {
								goldResult: data,
							});
						} catch (error) {
							console.error(error);
							realtimeUpdate(["account"], "/account", {
								goldResult: {
									success: false,
									message: ajaxErrorMsg,
								},
							});
						}
					},
				}),
			);
		})();
	}, []);

	const handleClick = () => {
		if (handler) {
			handler.open({
				name: "GM Gold",
				description: "",
				amount: 500,
				email,
				allowRememberMe: false,
				panelLabel: "Subscribe for $5/month",
			});
		}
	};

	return (
		<button
			className="btn btn-lg btn-primary"
			disabled={!handler}
			onClick={handleClick}
		>
			Sign Up for GM Gold
		</button>
	);
};

const handleCancel = async (e: MouseEvent) => {
	e.preventDefault();
	const result = await confirm(
		"Are you sure you want to cancel your GM Gold subscription?",
		{
			okText: "Yes",
			cancelText: "No",
		},
	);

	if (result) {
		try {
			const data = await fetchWrapper({
				url: `${ACCOUNT_API_URL}/gold_cancel.php`,
				method: "POST",
				data: {
					sport: process.env.SPORT,
				},
				credentials: "include",
			});
			realtimeUpdate(["account"], "/account", {
				goldResult: data,
			});
		} catch (err) {
			console.log(err);
			realtimeUpdate(["account"], "/account", {
				goldResult: {
					success: false,
					message: ajaxErrorMsg,
				},
			});
		}
	}
};

const UserInfo = ({
	goldUntilDateString,
	loggedIn,
	showGoldActive,
	showGoldCancelled,
	username,
}: {
	goldUntilDateString: string;
	loggedIn: boolean;
	showGoldActive: boolean;
	showGoldCancelled: boolean;
	username?: string;
}) => {
	const [logoutError, setLogoutError] = useState<string | undefined>();

	const handleLogout = async (event: MouseEvent) => {
		event.preventDefault();
		setLogoutError(undefined);

		try {
			await fetchWrapper({
				url: `${ACCOUNT_API_URL}/logout.php`,
				method: "POST",
				data: {
					sport: process.env.SPORT,
				},
				credentials: "include",
			});
			localActions.update({
				username: "",
			});
			realtimeUpdate(["account"], "/");
		} catch (error) {
			console.error(error);
			setLogoutError(ajaxErrorMsg);
		}
	};

	return (
		<>
			{!loggedIn ? (
				<p>
					You are not logged in!{" "}
					<a href="/account/login_or_register">
						Click here to log in or create an account.
					</a>{" "}
					If you have an account, your achievements will be stored in the cloud,
					combining achievements from leagues in different browsers and
					different computers.
				</p>
			) : (
				<p>
					Logged in as: <b>{username}</b> (
					<a href="" onClick={handleLogout}>
						Logout
					</a>
					)
				</p>
			)}
			{logoutError ? <p className="text-danger">{logoutError}</p> : null}
			{showGoldActive ? (
				<p>
					GM Gold: Active, renews for $5 on {goldUntilDateString} (
					<a href="/account/update_card">Update card</a> or{" "}
					<a href="" id="gold-cancel" onClick={handleCancel}>
						cancel
					</a>
					)
				</p>
			) : null}
			{showGoldCancelled ? (
				<p>GM Gold: Cancelled, expires {goldUntilDateString}</p>
			) : null}
		</>
	);
};

UserInfo.propTypes = {
	goldUntilDateString: PropTypes.string.isRequired,
	loggedIn: PropTypes.bool.isRequired,
	showGoldActive: PropTypes.bool.isRequired,
	showGoldCancelled: PropTypes.bool.isRequired,
	username: PropTypes.string,
};

const Account = ({
	achievements,
	email,
	goldMessage,
	goldSuccess,
	goldUntilDateString,
	loggedIn,
	showGoldActive,
	showGoldCancelled,
	showGoldPitch,
	username,
}: View<"account">) => {
	useTitleBar({
		title: "Your Account",
		hideNewWindow: true,
	});
	let goldPitchDiv: ReactNode = null;

	if (showGoldPitch) {
		goldPitchDiv = (
			<>
				<h2>GM Gold</h2>

				<div className="row">
					<div className="col-lg-8 col-md-10">
						<p>
							{GAME_NAME} is completely free. There will never be any{" "}
							<a
								href="http://en.wikipedia.org/wiki/Freemium"
								rel="noopener noreferrer"
								target="_blank"
							>
								"freemium"
							</a>{" "}
							or{" "}
							<a
								href="http://en.wikipedia.org/wiki/Free-to-play"
								rel="noopener noreferrer"
								target="_blank"
							>
								"pay-to-win"
							</a>{" "}
							bullshit here. Why? Because if a game charges you money for
							power-ups, the developer makes more money if they make their game
							frustratingly annoying to play without power-ups. Because of this,{" "}
							<b>freemium games always suck</b>.
						</p>

						<p>
							If you want to support {GAME_NAME} continuing to be a non-sucky
							game, sign up for GM Gold! It's only <b>$5/month</b>. What do you
							get? More like, what don't you get? You get no new features, no
							new improvements, no new anything. Just <b>no more ads</b> on{" "}
							<GameLinks thisGameText="this game" />. That's it. Why? For
							basically the same reason I won't make {GAME_NAME} freemium. I
							don't want the free version to become a crippled advertisement for
							the pay version. If you agree that the world is a better place
							when anyone anywhere can play <GameLinks noLinks />, sign up for
							GM Gold today!
						</p>

						{!loggedIn || !email ? (
							<p>
								<a href="/account/login_or_register">
									Log in or create an account
								</a>{" "}
								to sign up for GM Gold.
							</p>
						) : (
							<p>
								<StripeButton email={email} />
							</p>
						)}
					</div>
				</div>
			</>
		);
	}

	return (
		<>
			<div className="row">
				<div className="col-lg-8 col-md-10 ">
					<UserInfo
						goldUntilDateString={goldUntilDateString}
						loggedIn={loggedIn}
						showGoldActive={showGoldActive}
						showGoldCancelled={showGoldCancelled}
						username={username}
					/>
				</div>
			</div>

			{goldSuccess === true ? (
				<div className="alert alert-success">{goldMessage}</div>
			) : null}
			{goldSuccess === false ? (
				<div className="alert alert-danger">{goldMessage}</div>
			) : null}

			{goldPitchDiv}

			<h2>Achievements</h2>

			<p>
				You will only be awarded achievements in leagues where you have never
				used God Mode or set the difficulty to Easy.
			</p>

			{Object.entries(groupBy(achievements, "category")).map(
				([category, catAchivements]: [any, any[]]) => {
					return (
						<Fragment key={category}>
							<h3 className="mt-4">{category}</h3>
							<div
								className="row"
								style={{
									marginBottom: "-0.5rem",
								}}
							>
								{catAchivements.map(achievement => {
									return (
										<div key={achievement.slug} className="col-sm-4">
											<div
												className={classNames("card mb-2", {
													"list-group-item-success": achievement.count > 0,
													"text-muted": achievement.count === 0,
												})}
												key={achievement.slug}
												style={{
													minHeight: 109,
												}}
											>
												<div className="card-body">
													<h4 className="card-title">
														{achievement.name}
														{achievement.count > 1 ? (
															<span className="badge badge-pill badge-secondary float-right">
																{achievement.count}
															</span>
														) : null}
													</h4>
													<p className="card-text">{achievement.desc}</p>
												</div>
											</div>
										</div>
									);
								})}
							</div>
						</Fragment>
					);
				},
			)}
		</>
	);
};

Account.propTypes = {
	achievements: PropTypes.arrayOf(
		PropTypes.shape({
			category: PropTypes.string.isRequired,
			count: PropTypes.number.isRequired,
			desc: PropTypes.string.isRequired,
			name: PropTypes.string.isRequired,
			slug: PropTypes.string.isRequired,
		}),
	).isRequired,
	email: PropTypes.string,
	goldMessage: PropTypes.string,
	goldSuccess: PropTypes.bool,
	goldUntilDateString: PropTypes.string.isRequired,
	loggedIn: PropTypes.bool.isRequired,
	showGoldActive: PropTypes.bool.isRequired,
	showGoldCancelled: PropTypes.bool.isRequired,
	showGoldPitch: PropTypes.bool.isRequired,
	username: PropTypes.string,
};

export default Account;

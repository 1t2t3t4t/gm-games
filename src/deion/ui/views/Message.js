// @flow

import PropTypes from "prop-types";
import React from "react";
import { NewWindowLink, SafeHtml } from "../components";
import { helpers, setTitle } from "../util";
import type { Message as Message_ } from "../../common/types";

type MessageProps = {
    message: void | Message_,
};

const Message = ({ message }: MessageProps) => {
    if (!message) {
        setTitle("Message");

        return (
            <>
                <h1>Error</h1>
                <p>Message not found.</p>
            </>
        );
    }
    console.log(message);

    setTitle(`Message From ${message.from}`);

    return (
        <>
            {message.subject ? (
                <>
                    <h4>{message.subject}</h4>
                    <h5 className="mb-3">
                        From: {message.from}, {message.year} <NewWindowLink />
                    </h5>
                </>
            ) : (
                <h4 className="mb-3">
                    From: {message.from}, {message.year} <NewWindowLink />
                </h4>
            )}

            <SafeHtml dirty={message.text} />

            <p>
                <a href="#" onClick={() => window.history.back()}>
                    Previous Page
                </a>{" "}
                · <a href={helpers.leagueUrl(["inbox"])}>Inbox</a>
            </p>
        </>
    );
};

Message.propTypes = {
    message: PropTypes.shape({
        from: PropTypes.string.isRequired,
        text: PropTypes.string.isRequired,
        year: PropTypes.number.isRequired,
        subject: PropTypes.string,
    }),
};

export default Message;

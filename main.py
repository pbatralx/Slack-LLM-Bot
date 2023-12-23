import logging
import os

from slack_bolt import App, BoltContext
from slack_sdk.web import WebClient
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler

from app.bolt_listeners import before_authorize, register_listeners
from app.env import (
    USE_SLACK_LANGUAGE,
    SLACK_APP_LOG_LEVEL,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_API_TYPE,
    OPENAI_API_BASE,
    OPENAI_API_VERSION,
    OPENAI_DEPLOYMENT_ID,
    OPENAI_FUNCTION_CALL_MODULE_NAME,
)
from app.slack_ops import build_home_tab

from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore

if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    logging.basicConfig(level=SLACK_APP_LOG_LEVEL)

    oauth_settings = OAuthSettings(
        client_id=os.environ["SLACK_CLIENT_ID"],
        client_secret=os.environ["SLACK_CLIENT_SECRET"],
        scopes=[
            "commands",
            "app_mentions:read",
            "channels:history",
            "groups:history",
            "im:history",
            "mpim:history",
            "chat:write.public",
            "chat:write",
            "users:read"
        ],
        user_scopes=["chat:write"],
        installation_store=FileInstallationStore(
            base_dir="./data/installations"),
        state_store=FileOAuthStateStore(
            expiration_seconds=600, base_dir="./data/states")
    )

    app = App(
        # token=os.environ["SLACK_BOT_TOKEN"],
        oauth_settings=oauth_settings,
        before_authorize=before_authorize,
        process_before_response=True,
    )
    app.client.retry_handlers.append(
        RateLimitErrorRetryHandler(max_retry_count=2))

    register_listeners(app)

    @app.event("app_home_opened")
    def render_home_tab(client: WebClient, context: BoltContext):
        already_set_api_key = os.environ["OPENAI_API_KEY"]
        client.views_publish(
            user_id=context.user_id,
            view=build_home_tab(
                openai_api_key=already_set_api_key,
                context=context,
                single_workspace_mode=True,
            ),
        )

    if USE_SLACK_LANGUAGE is True:

        @app.middleware
        def set_locale(
            context: BoltContext,
            client: WebClient,
            next_,
        ):
            user_id = context.actor_user_id or context.user_id
            user_info = client.users_info(user=user_id, include_locale=True)
            context["locale"] = user_info.get("user", {}).get("locale")
            next_()

    @app.middleware
    def set_openai_api_key(context: BoltContext, next_):
        context["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
        context["OPENAI_MODEL"] = OPENAI_MODEL
        context["OPENAI_TEMPERATURE"] = OPENAI_TEMPERATURE
        context["OPENAI_API_TYPE"] = OPENAI_API_TYPE
        context["OPENAI_API_BASE"] = OPENAI_API_BASE
        context["OPENAI_API_VERSION"] = OPENAI_API_VERSION
        context["OPENAI_DEPLOYMENT_ID"] = OPENAI_DEPLOYMENT_ID
        context["OPENAI_FUNCTION_CALL_MODULE_NAME"] = OPENAI_FUNCTION_CALL_MODULE_NAME
        next_()

    # handler = SocketModeHandler(app)
    # handler.start()
    app.start(3000)

from __future__ import annotations

import logging
import os

import uvicorn

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    port = int(os.environ.get("PORT", "8080"))
    logger.info("Starting Tripzy on 0.0.0.0:%s", port)
    uvicorn.run(
        "travel_agent.web.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()

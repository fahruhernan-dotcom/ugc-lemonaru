"""Official Model Context Protocol (MCP) Server for Velora AI.
Exposes deterministic catalog and content tools to Hermes AI Orchestrator.
Compatible with MCP SDK 2.x (MCPServer).
"""

import asyncio
import json
import logging
from typing import Any, Dict

from mcp.server.mcpserver import MCPServer
from src.tools_service import HermesToolService

logger = logging.getLogger("velora.mcp")

# Initialize MCP Server with metadata
mcp_server = MCPServer(
    name="velora-ai-affiliate-engine",
    title="Velora AI Fashion Affiliate Engine",
    description="Hermes Agent tools for TikTok Shop Affiliate product intelligence, scoring, and content brief generation.",
    version="0.1.0"
)

tool_svc = HermesToolService()


@mcp_server.tool()
async def velora_ingest_catalog(csv_file_path: str) -> str:
    """Ingest, validate, and deduplicate a TikTok Shop fashion catalog from a CSV file.
    
    Args:
        csv_file_path: Absolute or workspace-relative path to the CSV file.
    """
    res = tool_svc.ingest_catalog(csv_file_path)
    return json.dumps(res, indent=2, default=str)


@mcp_server.tool()
async def velora_score_products() -> str:
    """Evaluate all stored products using the deterministic 6D formula and hard-stop eligibility gates."""
    res = tool_svc.score_all_products()
    return json.dumps(res, indent=2, default=str)


@mcp_server.tool()
async def velora_get_top_product() -> str:
    """Retrieve the highest-scoring eligible fashion product ready for content creation."""
    res = tool_svc.get_top_eligible_product()
    return json.dumps(res, indent=2, default=str)


@mcp_server.tool()
async def velora_generate_brief(product_id: str) -> str:
    """Generate a structured 9:16 video brief and export a Ready-to-Publish package for a product.
    
    Args:
        product_id: The external product ID or UUID of the product.
    """
    res = tool_svc.create_and_export_brief(product_id)
    return json.dumps(res, indent=2, default=str)


@mcp_server.tool()
async def velora_run_pipeline(csv_file_path: str) -> str:
    """Execute the complete vertical slice: Ingest -> Score -> Select Top -> Generate Brief -> Export Package.
    
    Args:
        csv_file_path: Path to the CSV catalog.
    """
    res = tool_svc.run_end_to_end_slice(csv_file_path)
    return json.dumps(res, indent=2, default=str)


async def main():
    logger.info("Starting Velora AI MCP server over stdio...")
    await mcp_server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())

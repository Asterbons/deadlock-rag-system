"""Neo4j driver factory — loads credentials from environment variables and verifies connectivity."""

from neo4j import GraphDatabase
import os
import logging

logger = logging.getLogger(__name__)


def get_driver():
    """Returns a Neo4j driver instance. Raises on connection failure."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable is not set")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {uri}")
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

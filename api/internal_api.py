import os
from datetime import datetime
import streamlit as st
import sqlalchemy
import pandas as pd
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv


def get_db_config(streamlit=True):
    if streamlit:
        DB_NAME = st.secrets.database.DB_NAME
        DB_USER = st.secrets.database.DB_USER
        DB_PASS = st.secrets.database.DB_PASS
        DB_HOST = st.secrets.database.DB_HOST
        DB_PORT = st.secrets.database.DB_PORT
        DB_ENV = st.secrets.database.DB_ENV
    else:
        load_dotenv()
        DB_NAME = os.environ.get("DB_NAME")
        DB_USER = os.environ.get("DB_USER")
        DB_PASS = os.environ.get("DB_PASS")
        DB_HOST = os.environ.get("DB_HOST")
        DB_PORT = os.environ.get("DB_PORT")
        DB_ENV = os.environ.get("DB_ENV")

    return {
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASS,
        "host": DB_HOST,
        "port": DB_PORT,
        "env": DB_ENV,
    }


def _get_connection(db_config):
    connection_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    engine = sqlalchemy.create_engine(connection_string)
    conn = engine.connect()
    return conn


class SynthetixAPI:
    SUPPORTED_CHAINS = {
        "arbitrum_mainnet": "Arbitrum",
        "base_mainnet": "Base",
        "optimism_mainnet": "Optimism (V2)",
        "eth_mainnet": "Ethereum",
    }

    def __init__(
        self, db_config: dict, environment: str = "prod", streamlit: bool = True
    ):
        """
        Initialize the SynthetixAPI.

        Args:
            environment (str): The environment to query data for ('prod' or 'dev')
        """
        self.db_config = get_db_config(streamlit)

        if db_config["env"] is not None:
            self.environment = self.db_config["env"]
        else:
            self.environment = environment

        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)

    def _create_engine(self):
        """Create and return a database engine with connection pooling."""
        connection_string = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['dbname']}"
        return sqlalchemy.create_engine(connection_string, pool_size=5, max_overflow=10)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.engine.dispose()

    @contextmanager
    def _get_connection(
        self,
    ) -> Generator[sqlalchemy.engine.base.Connection, None, None]:
        """Context manager for database connections."""
        connection = self.engine.connect()
        try:
            yield connection
        finally:
            connection.close()

    def _run_query(self, query: str) -> pd.DataFrame:
        """
        Run a SQL query and return the results as a DataFrame.

        Args:
            query (str): The SQL query to run.

        Returns:
            pandas.DataFrame: The query results.
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    # queries
    def get_volume(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "daily",
    ) -> pd.DataFrame:
        """
        Get trading volume data for a specified chain.

        Args:
            chain (str): Chain to query (e.g., 'base_mainnet', 'optimism_mainnet')
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            resolution (str): Data resolution ('daily' or 'hourly')

        Returns:
            pandas.DataFrame: Volume data with columns 'ts', 'volume', 'cumulative_volume'
        """
        query = f"""
        SELECT
            ts,
            volume,
            cumulative_volume
        FROM {self.environment}_{chain}.fct_perp_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_core_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
    ) -> pd.DataFrame:
        """
        Get core stats by chain.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g. 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: Core stats with columns 'ts', 'chain', 'collateral_value'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            SUM(collateral_value) AS collateral_value
        FROM {self.environment}_{chain}.fct_core_apr_{chain}
        WHERE 
            DATE(ts) >= '{start_date}' and DATE(ts) <= '{end_date}'
        GROUP BY ts, chain
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_core_stats_by_collateral(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "7d",
    ) -> pd.DataFrame:
        """
        Get core stats by collateral.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g. 'arbitrum_mainnet')
            resolution (str): Data resolution ('24h', '1d', '28d')

        Returns:
            pandas.DataFrame: TVL data with columns:
                'ts', 'label', 'chain', 'collateral_value', 'debt',
                'rewards_usd', 'apr', 'apr_rewards'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        # TODO: Remove this chain check once the underlying APR is available for all chains
        apr_str = f"apr_{resolution}{
                ' + apr_' + resolution + '_underlying as apr_' + resolution
                if chain in ['arbitrum_mainnet', 'base_mainnet']
                else ' as apr_' + resolution}"
        query = f"""
        SELECT 
            ts,
            '{chain_label}' AS chain,
            CONCAT(
                COALESCE(tokens.token_symbol, stats.collateral_type),
                ' (', '{chain_label}', ')'
            ) AS label,
            collateral_value,
            hourly_pnl,
            rewards_usd,
            {apr_str},
            apr_{resolution}_rewards
        FROM {self.environment}_{chain}.fct_core_apr_{chain} AS stats
        LEFT JOIN {self.environment}_seeds.{chain}_tokens AS tokens
            ON lower(stats.collateral_type) = lower(tokens.token_address)
        WHERE 
            DATE(ts) >= '{start_date}' and DATE(ts) <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_core_account_activity(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "daily",
    ) -> pd.DataFrame:
        """
        Get core account activity by action (Delegate, Withdraw, Claim).

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')
            resolution (str): Data resolution ('daily' or 'monthly')

        Returns:
            pandas.DataFrame: Account activity with columns:
                'date', 'chain', 'account_action', 'nof_accounts'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        trunc_resolution = "day" if resolution == "daily" else "month"
        query = f"""
        SELECT
            DATE_TRUNC('{trunc_resolution}', block_timestamp) AS date,
            '{chain_label}' AS chain,
            account_action as action,
            COUNT(DISTINCT account_id) AS nof_accounts
        FROM {self.environment}_{chain}.fct_core_account_activity_{chain}
        WHERE DATE(block_timestamp) >= '{start_date}' and DATE(block_timestamp) <= '{end_date}'
        GROUP BY 1, 2, 3
        ORDER BY 1
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_core_nof_stakers(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
    ) -> pd.DataFrame:
        """
        Get core number of stakers.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: NoF Stakers with columns:
                'date', 'chain', 'nof_stakers_daily'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            date,
            '{chain_label}' AS chain,
            nof_stakers_daily
        FROM {self.environment}_{chain}.fct_core_active_stakers_{chain}
        WHERE date >= '{start_date}' and date <= '{end_date}'
        ORDER BY date
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_perps_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "daily",
    ) -> pd.DataFrame:
        """
        Get perps stats by chain.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: Perps stats with columns:
                'ts', 'chain', 'volume', 'exchange_fees'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            volume,
            exchange_fees
        FROM {self.environment}_{chain}.fct_perp_stats_{resolution}_{chain}
        WHERE
            DATE(ts) >= '{start_date}' and DATE(ts) <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_perps_open_interest(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "daily",
    ) -> pd.DataFrame:
        """
        Get perps stats by chain.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: Perps stats with columns:
                'ts', 'chain', 'total_oi_usd'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        trunc_resolution = "day" if resolution == "daily" else "hour"
        query = f"""
        SELECT
            DATE_TRUNC('{trunc_resolution}', ts) AS ts,
            '{chain_label}' AS chain,
            MAX(total_oi_usd) as total_oi_usd
        FROM {self.environment}_{chain}.fct_perp_market_history_{chain}
        WHERE
            DATE(ts) >= '{start_date}' and DATE(ts) <= '{end_date}'
        GROUP BY 1, 2
        ORDER BY 2, 1
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_perps_markets_history(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
    ) -> pd.DataFrame:
        """
        Get perps markets history.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: Perps markets history with columns:
                'ts', 'chain', 'market_symbol', 'total_oi_usd', 'long_oi_pct', 'short_oi_pct'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            CONCAT(market_symbol, ' (', '{chain_label}', ')') as market_symbol,
            total_oi_usd,
            long_oi_pct,
            short_oi_pct
        FROM {self.environment}_{chain}.fct_perp_market_history_{chain}
        WHERE
            DATE(ts) >= '{start_date}' and DATE(ts) <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_perps_account_activity(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
    ) -> pd.DataFrame:
        """
        Get perps account activity. Active accounts are those that have
        settled at least one order in a day.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: Perps account activity with columns:
                'date', 'chain', 'nof_accounts'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts as date,
            '{chain_label}' AS chain,
            dau,
            mau
        FROM {self.environment}_{chain}.fct_perp_account_activity_{chain}
        WHERE DATE(ts) >= DATE('{start_date}') AND DATE(ts) <= DATE('{end_date}')
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_snx_token_buyback(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "base_mainnet",
    ) -> pd.DataFrame:
        """
        Get SNX token buyback data.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'base_mainnet')

        Returns:
            pandas.DataFrame: SNX token buyback data with columns:
                'ts', 'snx_amount', 'usd_amount'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            snx_amount,
            usd_amount
        FROM {self.environment}_{chain}.fct_buyback_daily_{chain}
        WHERE
            DATE(ts) >= '{start_date}' AND DATE(ts) <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    # V2 queries
    def get_perps_v2_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "optimism_mainnet",
        resolution: str = "daily",
    ) -> pd.DataFrame:
        """
        Get perps V2 stats.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'arbitrum_mainnet')

        Returns:
            pandas.DataFrame: Perps stats with columns:
                'ts', 'chain', 'volume', 'exchange_fees'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            volume,
            exchange_fees + liquidation_fees as exchange_fees
        FROM {self.environment}_{chain}.fct_v2_stats_{resolution}_{chain}
        WHERE
            DATE(ts) >= '{start_date}' AND DATE(ts) <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_perps_v2_open_interest(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "optimism_mainnet",
        resolution: str = "daily",
    ) -> pd.DataFrame:
        """
        Get perps V2 open interest.

        Args:
            start_date (datetime): Start date for the query
            end_date (datetime): End date for the query
            chain (str): Chain to query (e.g., 'optimism_mainnet')

        Returns:
            pandas.DataFrame: Open interest data with columns:
                'ts', 'chain', 'total_oi_usd'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            total_oi_usd
        FROM {self.environment}_{chain}.fct_v2_stats_{resolution}_{chain}
        WHERE
            DATE(ts) >= '{start_date}' AND DATE(ts) <= '{end_date}'
        ORDER BY ts
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

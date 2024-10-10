import os
from datetime import datetime, timedelta
import streamlit as st
import sqlalchemy
import pandas as pd
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator, List
from dotenv import load_dotenv


def get_db_config(streamlit=True):
    if streamlit:
        DB_NAME = st.secrets.database.DB_NAME
        DB_USER = st.secrets.database.DB_USER
        DB_PASS = st.secrets.database.DB_PASS
        DB_HOST = st.secrets.database.DB_HOST
        DB_PORT = st.secrets.database.DB_PORT
    else:
        load_dotenv()
        DB_NAME = os.environ.get("DB_NAME")
        DB_USER = os.environ.get("DB_USER")
        DB_PASS = os.environ.get("DB_PASS")
        DB_HOST = os.environ.get("DB_HOST")
        DB_PORT = os.environ.get("DB_PORT")

    return {
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASS,
        "host": DB_HOST,
        "port": DB_PORT,
    }


def get_connection(db_config):
    connection_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    engine = sqlalchemy.create_engine(connection_string)
    conn = engine.connect()
    return conn


class SynthetixAPI:
    SUPPORTED_CHAINS = {
        "arbitrum_mainnet": "Arbitrum",
        "base_mainnet": "Base",
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
        self.environment = environment
        self.db_config = get_db_config(streamlit)
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
    def get_connection(
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
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

    # queries
    def get_volume(
        self,
        chain: str,
        start_date: datetime,
        end_date: datetime,
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
        with self.get_connection() as conn:
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
            ts >= '{start_date}' and ts <= '{end_date}'
        GROUP BY ts, chain
        ORDER BY ts
        """
        with self.get_connection() as conn:
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
            apr_{resolution},
            apr_{resolution}_rewards
        FROM {self.environment}_{chain}.fct_core_apr_{chain} AS stats
        LEFT JOIN {self.environment}_seeds.{chain}_tokens AS tokens
            ON lower(stats.collateral_type) = lower(tokens.token_address)
        WHERE 
            ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_core_account_activity(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "day",
    ) -> pd.DataFrame:
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        with delegated as (
            select distinct
                block_timestamp,
                account_id,
                'Delegated' as action
            from {self.environment}_raw_{chain}.core_delegation_updated_{chain} as core
        ),
        withdrawn as (
            select
                block_timestamp,
                account_id,
                'Withdrawn' as action
            from {self.environment}_raw_{chain}.core_withdrawn_{chain} as core
        ),
        claimed as (
            select
                block_timestamp,
                account_id,
                'Claimed' as action
            from {self.environment}_raw_{chain}.core_rewards_claimed_{chain} as core
        ),
        combined as (
            select * from delegated
            union all
            select * from withdrawn
            union all
            select * from claimed
        )
        select
            date_trunc('{resolution}', block_timestamp) as date,
            '{chain_label}' as chain,
            action,
            count(distinct account_id) as nof_accounts
        from combined
        where block_timestamp >= '{start_date}' and block_timestamp <= '{end_date}'
        group by
            date, action
        order by date desc
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_core_nof_stakers(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
    ) -> pd.DataFrame:
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        with delegation_updated as (
            select
                block_timestamp,
                account_id,
                amount
            from {self.environment}_raw_{chain}.core_delegation_updated_{chain} as core
        ),

        dim as (
            select  
                d.ts,
                accounts.account_id
            from (
                select 
                    generate_series(
                        date_trunc('day', date('2023-12-15')),
                        date_trunc('day', current_date), '1 day'::interval
                    ) as ts
            ) as d
            cross join (
                select distinct account_id from delegation_updated
            ) as accounts
        ),

        stakers as (
            select 
                ts,
                dim.account_id,
                case when coalesce(last(amount) over (
                    partition by dim.account_id
                    order by ts
                    rows between unbounded preceding and current row
                ), 0) = 0 then 0 else 1 end as is_staking
            from dim
            left join delegation_updated
                on dim.ts = date(delegation_updated.block_timestamp)
                and dim.account_id = delegation_updated.account_id
        )

        select
            ts,
            '{chain_label}' as chain,
            sum(is_staking) as nof_stakers
        from stakers
        where ts >= '{start_date}' and ts <= '{end_date}'
        group by ts
        order by ts asc
        """
        with self.get_connection() as conn:
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
            ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
        with self.get_connection() as conn:
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
                'ts', 'chain', 'market_symbol', 'size_usd', 'long_oi_pct', 'short_oi_pct'
        """
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
        SELECT
            ts,
            '{chain_label}' AS chain,
            CONCAT(market_symbol, ' (', '{chain_label}', ')') as market_symbol,
            size_usd,
            long_oi_pct,
            short_oi_pct
        FROM {self.environment}_{chain}.fct_perp_market_history_{chain}
        WHERE
            ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_perps_account_activity(
        self,
        start_date: datetime,
        end_date: datetime,
        chain: str = "arbitrum_mainnet",
        resolution: str = "day",
    ) -> pd.DataFrame:
        chain_label = self.SUPPORTED_CHAINS[chain]
        query = f"""
            with user_stats as (
                select 
                    date_trunc('{resolution}', block_timestamp) as date,
                    count(distinct account_id) as nof_accounts
                from {self.environment}_raw_{chain}.perp_order_settled_{chain}
                where block_timestamp >= '{start_date}' and block_timestamp <= '{end_date}'
                group by date_trunc('{resolution}', block_timestamp)
            )
            select
                date,
                '{chain_label}' as chain,
                nof_accounts,
                nof_accounts - lag(nof_accounts, 1, nof_accounts) over (order by date asc) as new_accounts
            from user_stats
            order by date asc
        """
        with self.get_connection() as conn:
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
        query = f"""
        SELECT
            ts,
            snx_amount,
            usd_amount
        FROM {self.environment}_{chain}.fct_buyback_daily_{chain}
        WHERE
            ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

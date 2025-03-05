import streamlit as st
from dashboards.system_monitor.modules.settings import settings
from synthetix.utils import format_ether

st.markdown("# Leveraged Token Rewards")
settings([8453, 10])

api = st.session_state.api
snx = st.session_state.snx
if st.session_state.network_id == 10:
    network_name = "optimism"
    reward_amount = 15000
    reward_token = "OP"
    decimals = 18
elif st.session_state.network_id == 8453:
    network_name = "base"
    reward_amount = 30000
    reward_token = "USDC"
    decimals = 6
else:
    raise ValueError("Unknown network")


# get the timestamp of the last redemption
query_last_redemption = f"""
select
    max(block_timestamp) as last_redemption_ts,
    max(block_number) as last_redemption_block
from prod_raw_{network_name}_mainnet.{"tlx_" if network_name == "optimism" else ""}lt_redeemed_{network_name}_mainnet
"""
df_last_redemption = api._run_query(query_last_redemption)
last_redemption_ts = df_last_redemption["last_redemption_ts"].values[0]
last_redemption_block = df_last_redemption["last_redemption_block"].values[0]

# run the leaderboard query
query = f"""
select
    epoch_start,
    account,
    total_fees_paid,
    fees_paid_pct,
    fees_rank,
    volume,
    volume_pct,
    volume_rank
from prod_{network_name}_mainnet.lt_leaderboard_{network_name}
where epoch_start > date '2025-01-14'
order by epoch_start desc, rank asc
"""
df = api._run_query(query)

epochs = df["epoch_start"].unique()

# display the results
st.selectbox("Epoch", epochs, key="epoch")
df_filt = df[df["epoch_start"] == st.session_state.epoch]
df_filt["reward"] = df_filt["volume_pct"] * reward_amount
df_filt["reward_token"] = reward_token

st.dataframe(df_filt, use_container_width=True, hide_index=True)
st.write(
    f"Last redemption recorded at {last_redemption_ts} (block {last_redemption_block})"
)

# reward calculations
st.markdown("## Reward Calculations")
st.write(f"Total reward amount: {reward_amount} {reward_token}")

# get the data
addresses = [
    snx.web3.to_checksum_address(address) for address in df_filt["account"].values
]
amounts = [
    str(format_ether(reward, decimals=decimals)) for reward in df_filt["reward"].values
]
address_map = dict(zip(addresses, amounts))

# print it
st.markdown("## Merkle Input")
st.write(address_map)

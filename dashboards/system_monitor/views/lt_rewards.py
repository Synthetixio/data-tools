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
    rank,
    account,
    total_fees_paid,
    fees_paid_pct    
from prod_{network_name}_mainnet.lt_leaderboard
where epoch_start > date '2025-01-14'
order by epoch_start desc, rank asc
"""
df = api._run_query(query)

epochs = df["epoch_start"].unique()

# display the results
st.selectbox("Epoch", epochs, key="epoch")
df_filt = df[df["epoch_start"] == st.session_state.epoch]
df_filt["reward"] = df_filt["fees_paid_pct"] * reward_amount
df_filt["reward_token"] = reward_token

st.dataframe(df_filt, use_container_width=True, hide_index=True)
st.write(
    f"Last redemption recorded at {last_redemption_ts} (block {last_redemption_block})"
)

# reward calculations
st.markdown("## Reward Calculations")
st.write(f"Total reward amount: {reward_amount} {reward_token}")

abi = [
    {
        "inputs": [
            {"internalType": "address[]", "name": "users", "type": "address[]"},
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"},
        ],
        "name": "increaseUserRewards",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]
contract = snx.web3.eth.contract(abi=abi)

# get the data
addresses = [
    snx.web3.to_checksum_address(address) for address in df_filt["account"].values
]
amounts = [
    format_ether(reward, decimals=decimals) for reward in df_filt["reward"].values
]

# print it
st.markdown("## Inputs")
st.write("Addresses:", addresses)
st.write("Reward amounts:", amounts)

# format the data
st.markdown("## Transaction Data")
data = contract.encode_abi(fn_name="increaseUserRewards", args=[addresses, amounts])

st.write(data)
st.markdown("Decode ABI data [here](https://openchain.xyz/tools/abi) to verify")

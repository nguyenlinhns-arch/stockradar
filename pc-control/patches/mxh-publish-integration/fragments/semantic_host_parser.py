# >>> V7_MXH_PUBLISH_INTEGRATION
MXH_BRIDGE_PREFIX='MXH_V1:'
def parse_mxh_bridge(goal):
    if not isinstance(goal,str) or not goal.startswith(MXH_BRIDGE_PREFIX):return None
    from src.connectors.mxh.contract import parse_mxh_bridge as _parse
    return _parse(goal)
# <<< V7_MXH_PUBLISH_INTEGRATION

            # >>> V7_MXH_PUBLISH_INTEGRATION
            mxh_bridge=parse_mxh_bridge(payload.get('goal'))
            if mxh_bridge is not None:
                if payload.get('steps'):raise ValueError('MXH_BRIDGE_STEPS_FORBIDDEN')
                mxh_action,mxh_args=mxh_bridge
                from src.connectors.mxh.contract import mxh_action_risk
                mxh_risk=mxh_action_risk(mxh_action)
                permission({'risk':mxh_risk,'action':'mxh_'+mxh_action},self.host.config())
                if mxh_risk!='READ' and self.host.RELIABILITY:self.host.RELIABILITY.mutation()
                from src.connectors.mxh.adapter import MxhHubAdapter
                result=MxhHubAdapter().execute(mxh_action,mxh_args)
                return {**result,'bridge':'MXH_V1','planner':'ChatGPT','task_id':self.cid}
            # <<< V7_MXH_PUBLISH_INTEGRATION

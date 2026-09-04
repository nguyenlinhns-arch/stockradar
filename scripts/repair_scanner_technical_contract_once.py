from pathlib import Path

path = Path("scripts/bootstrap_kbs_hose_data.py")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        '''        current_vol=pd.to_numeric(pd.Series([b.get("total_volume")]),errors="coerce").iloc[0]\n        ig=intraday[intraday["ticker"]==ticker].copy() if not intraday.empty else pd.DataFrame()\n        same_time_ratio=None; current_cum=None; projected_vol=None\n''',
        '''        current_vol=pd.to_numeric(pd.Series([b.get("total_volume")]),errors="coerce").iloc[0]\n        daily_bar_count=int(len(g))\n        board_pct_change=pd.to_numeric(pd.Series([b.get("pct_change")]),errors="coerce").iloc[0]\n        if pd.notna(board_pct_change):\n            pct_change=float(board_pct_change)\n        elif len(close)>=2 and float(close.iloc[-2]) != 0:\n            pct_change=(current_price/float(close.iloc[-2])-1.0)*100.0\n        else:\n            pct_change=0.0\n        down_for_pp=g[g["close"].diff()<0].tail(10)\n        down_date_set={ts.date() for ts in down_for_pp["timestamp"] if pd.notna(ts)}\n        ig=intraday[intraday["ticker"]==ticker].copy() if not intraday.empty else pd.DataFrame()\n        same_time_ratio=None; current_cum=None; projected_vol=None; same_time_down_cums=[]\n''',
    ),
    (
        '''                        cum=float(dg["volume"].sum())\n                        pri.append(cum)\n                        full=daily_by_date.get(d)\n''',
        '''                        cum=float(dg["volume"].sum())\n                        pri.append(cum)\n                        if d in down_date_set:\n                            same_time_down_cums.append(cum)\n                        full=daily_by_date.get(d)\n''',
    ),
    (
        '''        if current_cum is None and pd.notna(current_vol): current_cum=float(current_vol)\n        rvol=(current_cum/vol20) if current_cum is not None and vol20 and vol20>0 else None\n        down=g[g["close"].diff()<0].tail(10)\n        max_down_vol10=float(down["volume"].max()) if not down.empty else None\n        pocket_vol_pass=bool(projected_vol and max_down_vol10 and projected_vol>max_down_vol10)\n''',
        '''        if current_cum is None and pd.notna(current_vol): current_cum=float(current_vol)\n        rvol=(current_cum/vol20) if current_cum is not None and vol20 and vol20>0 else None\n        rvol_progress_adjusted=(projected_vol/vol20) if projected_vol is not None and vol20 and vol20>0 else rvol\n        down=down_for_pp\n        max_down_vol10=float(down["volume"].max()) if not down.empty else None\n        same_time_max_down=max(same_time_down_cums) if same_time_down_cums else None\n        if current_cum is not None and same_time_max_down is not None:\n            pocket_vol_pass=bool(current_cum>same_time_max_down)\n        else:\n            pocket_vol_pass=bool(projected_vol and max_down_vol10 and projected_vol>max_down_vol10)\n''',
    ),
    (
        '''            "ticker":ticker,"price":current_price,"last_daily_close":last,"ma10":ma10,"ma20":ma20,"ma50":ma50,"ma150":ma150,"ma200":ma200,\n            "vol20":vol20,"current_cum_volume":current_cum,"rvol_vs_full_day_vol20":rvol,"same_time_volume_ratio":same_time_ratio,"projected_full_day_volume":projected_vol,\n            "max_down_volume_10":max_down_vol10,"pocket_pivot_volume_pass_intraday_projection":pocket_vol_pass,"pivot20":pivot20,"distance_to_pivot_pct":dist,\n''',
        '''            "ticker":ticker,"price":current_price,"pct_change":pct_change,"daily_bar_count":daily_bar_count,"last_daily_close":last,"ma10":ma10,"ma20":ma20,"ma50":ma50,"ma150":ma150,"ma200":ma200,\n            "vol20":vol20,"current_cum_volume":current_cum,"rvol_vs_full_day_vol20":rvol,"rvol_progress_adjusted":rvol_progress_adjusted,"same_time_volume_ratio":same_time_ratio,"projected_full_day_volume":projected_vol,\n            "max_down_volume_10":max_down_vol10,"same_time_max_down_volume_10":same_time_max_down,"pocket_pivot_volume_pass":pocket_vol_pass,"pocket_pivot_volume_pass_intraday_projection":pocket_vol_pass,"pivot20":pivot20,"distance_to_pivot_pct":dist,\n''',
    ),
    (
        '''            "bollinger_width_pct":bb_width,"bollinger_squeeze":squeeze,"volume_dry_up_5d":vol_dry,"vcp_contraction_score":vcp_score,\n            "source":SOURCE_ID,"rights_publication":"BLOCKED_PENDING_TERMS_REVIEW"\n''',
        '''            "bollinger_width_pct":bb_width,"bollinger_squeeze":squeeze,"volume_dry_up_5d":vol_dry,"vcp_contraction_score":vcp_score,\n            "technical_history_eligible":bool(daily_bar_count>=210),\n            "source":SOURCE_ID,"rights_publication":"BLOCKED_PENDING_TERMS_REVIEW"\n''',
    ),
]

for i, (old, new) in enumerate(replacements, start=1):
    if old not in text:
        raise SystemExit(f"repair anchor {i} not found")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("patched technical producer contract")

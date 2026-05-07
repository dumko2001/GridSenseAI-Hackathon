"""
Human-in-the-Loop Override Engine
SLDC operators know things the model doesn't:
- Planned maintenance tomorrow (forecast should be 0 or reduced)
- Grid curtailment order from RLDC (forecast capped by dispatch)
- New inverter commissioning (capacity increase not in historical data)
- Dust storm expected (operator intuition > weather model)

This module merges operator overrides with AI forecasts.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class OverrideRule:
    """Single override rule."""
    def __init__(self, plant_id: str, start_time: str, end_time: str,
                 override_type: str, value: Optional[float] = None,
                 reason: str = "", created_by: str = "operator"):
        self.plant_id = plant_id
        self.start_time = pd.to_datetime(start_time)
        self.end_time = pd.to_datetime(end_time)
        self.override_type = override_type  # 'zero', 'cap', 'scale', 'absolute'
        self.value = value
        self.reason = reason
        self.created_by = created_by
        self.created_at = pd.Timestamp.now()

    def to_dict(self):
        return {
            "plant_id": self.plant_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "override_type": self.override_type,
            "value": self.value,
            "reason": self.reason,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


class OverrideManager:
    """Store and apply operator overrides."""
    def __init__(self):
        self.rules: List[OverrideRule] = []

    def add_rule(self, rule: OverrideRule):
        # Remove overlapping rules for same plant
        self.rules = [r for r in self.rules if not (
            r.plant_id == rule.plant_id and
            r.start_time <= rule.end_time and
            r.end_time >= rule.start_time
        )]
        self.rules.append(rule)
        return rule

    def get_active_rules(self, plant_id: str, timestamp: pd.Timestamp):
        return [r for r in self.rules if r.plant_id == plant_id and r.start_time <= timestamp <= r.end_time]

    def apply_overrides(self, forecast_df: pd.DataFrame) -> pd.DataFrame:
        """Apply all active overrides to forecast DataFrame."""
        df = forecast_df.copy()
        df["overridden"] = False
        df["override_reason"] = ""

        for _, row in df.iterrows():
            ts = pd.to_datetime(row["timestamp"])
            pid = row["plant_id"]
            active = self.get_active_rules(pid, ts)
            if not active:
                continue
            rule = active[0]  # Take first if multiple
            val = row["final_forecast_MW"]

            if rule.override_type == "zero":
                val = 0.0
            elif rule.override_type == "cap" and rule.value is not None:
                val = min(val, rule.value)
            elif rule.override_type == "scale" and rule.value is not None:
                val = val * rule.value
            elif rule.override_type == "absolute" and rule.value is not None:
                val = rule.value

            df.at[_, "final_forecast_MW"] = val
            df.at[_, "overridden"] = True
            df.at[_, "override_reason"] = f"Operator override: {rule.reason}"
            if "explanation" in df.columns:
                base_explanation = str(df.at[_, "explanation"]).strip()
                suffix = df.at[_, "override_reason"]
                df.at[_, "explanation"] = f"{base_explanation} {suffix}".strip()

        return df

    def list_rules(self, plant_id: Optional[str] = None):
        rules = self.rules
        if plant_id:
            rules = [r for r in rules if r.plant_id == plant_id]
        return [r.to_dict() for r in rules]

    def clear_expired(self):
        now = pd.Timestamp.now()
        self.rules = [r for r in self.rules if r.end_time >= now]


# Global singleton for API usage
_override_manager = None

def get_override_manager():
    global _override_manager
    if _override_manager is None:
        _override_manager = OverrideManager()
    return _override_manager


if __name__ == "__main__":
    mgr = get_override_manager()
    # Example: Pavagada solar down for maintenance April 5, 10:00-14:00
    mgr.add_rule(OverrideRule(
        plant_id="SOL_PAVAGADA_100",
        start_time="2025-04-05 10:00",
        end_time="2025-04-05 14:00",
        override_type="zero",
        reason="Inverter maintenance scheduled",
        created_by="SLDC_operator_Rajesh"
    ))
    print("Active rules:", mgr.list_rules())

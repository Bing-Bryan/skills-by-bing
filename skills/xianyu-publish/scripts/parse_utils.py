#!/usr/bin/env python3
"""Shared parsing for Xianyu price and count fields ('¥7,299', '1.2万', '1万2')."""

from __future__ import annotations

import re
from typing import Optional

# Condition tokens like 9成新 / 9.5成新 / 99新 that would otherwise be read as numbers.
_NOISE = re.compile(r"\d+(?:\.\d+)?成新|\d{2}新")
_WAN = re.compile(r"(\d+(?:\.\d+)?)\s*[万w]\s*(\d)?", re.IGNORECASE)
_QIAN = re.compile(r"(\d+(?:\.\d+)?)\s*千")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def parse_amount(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    text = str(value).replace(",", "").replace("，", "").replace("¥", "").replace("￥", "")
    text = _NOISE.sub(" ", text)
    match = _WAN.search(text)
    if match:
        amount = float(match.group(1)) * 10000
        if match.group(2):
            amount += float(match.group(2)) * 1000
        return amount
    match = _QIAN.search(text)
    if match:
        return float(match.group(1)) * 1000
    match = _NUMBER.search(text)
    return float(match.group()) if match else None


def parse_price(value: object) -> Optional[float]:
    amount = parse_amount(value)
    return amount if amount is not None and amount > 0 else None

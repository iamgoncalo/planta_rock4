#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v5 — Gemini via google-genai (SDK novo)

Substitui app/services/chat.py com SDK actual (google-genai, não o deprecated).
Troca requirements: google-generativeai -> google-genai.
Logs via print(flush=True) para garantir visibilidade no Railway.
"""

import base64
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),
])

FILES = {
    'app/services/chat.py': (
        'IiIiClBsYW50YU9TIMK3IENoYXQgc2VydmljZSDCtyB2NSAoZ29vZ2xlLWdlbmFpIG5vdm8gU0RL'
        'KQo9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0K'
        'UmVzcG9zdGEgdmlhIEdlbWluaSAyLjUgRmxhc2ggY29tIGNvbnRleHRvIGxpdmUgaW5qZWN0YWRv'
        'LgpGYWxsYmFjayByZWdyYS1iYXNlZCBlbSBQVC1QVCBzZSBhIGtleSBmYWxoYXIuCgpNYW50w6lt'
        'IGEgYXNzaW5hdHVyYTogYW5zd2VyX2NoYXQobWVzc2FnZSwgbGl2ZV9wYXlsb2FkLCByb3V0ZSkg'
        'LT4gQ2hhdFJlc3BvbnNlCiIiIgpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCgpp'
        'bXBvcnQgb3MKaW1wb3J0IHN5cwppbXBvcnQgdGltZQppbXBvcnQgdHJhY2ViYWNrCmZyb20gdHlw'
        'aW5nIGltcG9ydCBBbnksIE9wdGlvbmFsCgpmcm9tIGFwcC5tb2RlbHMuY2hhdCBpbXBvcnQgQ2hh'
        'dFJlc3BvbnNlCmZyb20gYXBwLm1vZGVscy5zZWN0aW9ucyBpbXBvcnQgTGl2ZVBheWxvYWQgICMg'
        'dHlwZTogaWdub3JlCmZyb20gYXBwLm1vZGVscy5yb3V0aW5nIGltcG9ydCBCYXRocm9vbVJvdXRl'
        'RGVjaXNpb24gICMgdHlwZTogaWdub3JlCgoKZGVmIF9sb2cobGV2ZWw6IHN0ciwgbXNnOiBzdHIp'
        'IC0+IE5vbmU6CiAgICAiIiJMb2cgY29tIGZsdXNoIHBhcmEgZ2FyYW50aXIgdmlzaWJpbGlkYWRl'
        'IG5vcyBsb2dzIFJhaWx3YXkuIiIiCiAgICBwcmludChmIltjaGF0LnY1XSB7bGV2ZWx9OiB7bXNn'
        'fSIsIGZsdXNoPVRydWUpCgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgR2VtaW5pIGNvbmZpZwoj'
        'IC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0KR0VNSU5JX0FQSV9LRVkgPSBvcy5nZXRlbnYoIkdFTUlOSV9B'
        'UElfS0VZIiwgIiIpLnN0cmlwKCkKR0VNSU5JX01PREVMID0gb3MuZ2V0ZW52KCJHRU1JTklfTU9E'
        'RUwiLCAiZ2VtaW5pLTIuNS1mbGFzaCIpLnN0cmlwKCkKR0VNSU5JX1RJTUVPVVRfUyA9IGZsb2F0'
        'KG9zLmdldGVudigiR0VNSU5JX1RJTUVPVVRfUyIsICIxMCIpKQpHRU1JTklfTUFYX1RPS0VOUyA9'
        'IGludChvcy5nZXRlbnYoIkdFTUlOSV9NQVhfVE9LRU5TIiwgIjUxMiIpKQpHRU1JTklfVEVNUEVS'
        'QVRVUkUgPSBmbG9hdChvcy5nZXRlbnYoIkdFTUlOSV9URU1QRVJBVFVSRSIsICIwLjQiKSkKCl9s'
        'b2coIkJPT1QiLCBmImNoYXQudjUgYSBpbmljaWFyIMK3IG1vZGVsPXtHRU1JTklfTU9ERUx9IMK3'
        'IGtleT17J3NldCcgaWYgR0VNSU5JX0FQSV9LRVkgZWxzZSAnTUlTU0lORyd9IikKCiMgLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLQojIEluaXQgR2VtaW5pIGNsaWVudCAoY29sZCBzdGFydCkg4oCUIHVzYSBT'
        'REsgbm92byAiZ29vZ2xlLWdlbmFpIgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KX0dFTUlOSV9DTElF'
        'TlQ6IE9wdGlvbmFsW0FueV0gPSBOb25lCl9HRU1JTklfVFlQRVM6IE9wdGlvbmFsW0FueV0gPSBO'
        'b25lCl9HRU1JTklfQVZBSUxBQkxFID0gRmFsc2UKX0dFTUlOSV9JTklUX0VSUk9SOiBPcHRpb25h'
        'bFtzdHJdID0gTm9uZQpfTEFTVF9DQUxMX0VSUk9SOiBPcHRpb25hbFtzdHJdID0gTm9uZQpfTEFT'
        'VF9DQUxMX09LX1RTOiBPcHRpb25hbFtmbG9hdF0gPSBOb25lCl9MQVNUX0NBTExfRVJSX1RTOiBP'
        'cHRpb25hbFtmbG9hdF0gPSBOb25lCgppZiBHRU1JTklfQVBJX0tFWToKICAgIHRyeToKICAgICAg'
        'ICBmcm9tIGdvb2dsZSBpbXBvcnQgZ2VuYWkgICMgdHlwZTogaWdub3JlCiAgICAgICAgZnJvbSBn'
        'b29nbGUuZ2VuYWkgaW1wb3J0IHR5cGVzIGFzIGdlbmFpX3R5cGVzICAjIHR5cGU6IGlnbm9yZQog'
        'ICAgICAgIF9HRU1JTklfQ0xJRU5UID0gZ2VuYWkuQ2xpZW50KGFwaV9rZXk9R0VNSU5JX0FQSV9L'
        'RVkpCiAgICAgICAgX0dFTUlOSV9UWVBFUyA9IGdlbmFpX3R5cGVzCiAgICAgICAgX0dFTUlOSV9B'
        'VkFJTEFCTEUgPSBUcnVlCiAgICAgICAgX2xvZygiQk9PVCIsIGYiZ29vZ2xlLWdlbmFpIFNESyBP'
        'SyDCtyBjbGllbnQgY3JpYWRvIMK3IG1vZGVsPXtHRU1JTklfTU9ERUx9IikKICAgIGV4Y2VwdCBJ'
        'bXBvcnRFcnJvciBhcyBlOgogICAgICAgIF9HRU1JTklfSU5JVF9FUlJPUiA9IGYiSW1wb3J0RXJy'
        'b3I6IHtlfSIKICAgICAgICBfbG9nKCJCT09UIiwgZiJnb29nbGUtZ2VuYWkgTsODTyBpbnN0YWxh'
        'ZG86IHtlfSIpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgX0dFTUlOSV9JTklU'
        'X0VSUk9SID0gZiJ7ZS5fX2NsYXNzX18uX19uYW1lX199OiB7ZX0iCiAgICAgICAgX2xvZygiQk9P'
        'VCIsIGYiZ29vZ2xlLWdlbmFpIGZhbGhvdSBubyBpbml0OiB7X0dFTUlOSV9JTklUX0VSUk9SfSIp'
        'CiAgICAgICAgdHJhY2ViYWNrLnByaW50X2V4YygpCmVsc2U6CiAgICBfR0VNSU5JX0lOSVRfRVJS'
        'T1IgPSAiR0VNSU5JX0FQSV9LRVkgbsOjbyBkZWZpbmlkYSIKICAgIF9sb2coIkJPT1QiLCBfR0VN'
        'SU5JX0lOSVRfRVJST1IpCgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgS2V5d29yZHMgKGZhbGxi'
        'YWNrKQojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KX0tFWVdPUkRTX1dISUNIID0gKCJ3aGljaCIsICJx'
        'dWFsIiwgIm9uZGUiLCAid2hlcmUiKQpfS0VZV09SRFNfRkFTVEVTVCA9ICgiZmFzdGVzdCIsICJx'
        'dWljayIsICJyYXBpZCIsICJtYWlzIHJhcGlkbyIsICJtYWlzIHLDoXBpZG8iLCAicmFwaWRvIiwg'
        'InLDoXBpZG8iKQpfS0VZV09SRFNfRlVMTCA9ICgiZnVsbCIsICJjaGVpbyIsICJsb3RhZG8iLCAi'
        'Y3Jvd2RlZCIsICJvY3VwYWRvIiwgImNoZWlhIikKX0tFWVdPUkRTX0FWT0lEID0gKCJhdm9pZCIs'
        'ICJldml0YXIiLCAic2tpcCIsICJub3QgZ28iLCAibmFvIGlyIiwgIm7Do28gaXIiKQpfS0VZV09S'
        'RFNfU0VOU09SID0gKCJzZW5zb3IiLCAiaXIiLCAid2lmaSIsICJjYW1lcmEiLCAibG9yYXdhbiIs'
        'ICJzY29yIikKX0tFWVdPUkRTX1NIT1cgPSAoInNob3ciLCAiY29uY2VydG8iLCAiYXJ0aXN0YSIs'
        'ICJwYWxjbyIsICJzdGFnZSIsICJiYW5kIiwgImJhbmRhIikKX0tFWVdPUkRTX09QUyA9ICgib3Bl'
        'cmF0aW9ucyIsICJvcHMiLCAic3RhZmYiLCAiYWxlcnQiLCAiYWxlcnRhIiwgIm9wZXJhw6fDtWVz'
        'IiwgIm9wZXJhdGlvbiIpCgoKZGVmIF9jb250YWluc19hbnkodGV4dDogc3RyLCBrZXl3b3Jkczog'
        'dHVwbGVbc3RyLCAuLi5dKSAtPiBib29sOgogICAgbG93ZXIgPSB0ZXh0Lmxvd2VyKCkKICAgIHJl'
        'dHVybiBhbnkoayBpbiBsb3dlciBmb3IgayBpbiBrZXl3b3JkcykKCgojIC0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0KIyBDb250ZXh0byBsaXZlIOKGkiBibG9jbyBjb21wYWN0byBwYXJhIG8gTExNCiMgLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLQpkZWYgX2J1aWxkX2NvbnRleHRfYmxvY2soCiAgICBsaXZlX3BheWxv'
        'YWQ6IE9wdGlvbmFsW0xpdmVQYXlsb2FkXSwKICAgIHJvdXRlOiBPcHRpb25hbFtCYXRocm9vbVJv'
        'dXRlRGVjaXNpb25dLAopIC0+IHN0cjoKICAgIGlmIGxpdmVfcGF5bG9hZCBpcyBOb25lOgogICAg'
        'ICAgIHJldHVybiAiRVNUQURPOiBzZW0gZGFkb3MgbGl2ZSBkaXNwb27DrXZlaXMgbmVzdGUgbW9t'
        'ZW50by4iCgogICAga3BpcyA9IGxpdmVfcGF5bG9hZC5rcGlzCiAgICBzZWN0aW9ucyA9IGxpc3Qo'
        'bGl2ZV9wYXlsb2FkLnNlY3Rpb25zKQoKICAgIGxpbmVzOiBsaXN0W3N0cl0gPSBbXQogICAgbGlu'
        'ZXMuYXBwZW5kKCIjIyBFU1RBRE8gTElWRSBETyBGRVNUSVZBTCAoUm9jayBpbiBSaW8gTGlzYm9h'
        'IMK3IFBhcnF1ZSBUZWpvKSIpCiAgICBsaW5lcy5hcHBlbmQoCiAgICAgICAgZiItIE9jdXBhw6fD'
        'o28gbcOpZGlhOiB7a3Bpcy5hdmdfb2N1cGFjYW9fcGN0Oi4wZn0lICAiCiAgICAgICAgZiLCtyBG'
        'aWxhIHRvdGFsOiB7a3Bpcy50b3RhbF9maWxhfSAgIgogICAgICAgIGYiwrcgQ3LDrXRpY29zOiB7'
        'a3Bpcy5jcml0aWNhbF9zZWN0aW9uc30iCiAgICApCiAgICBsaW5lcy5hcHBlbmQoCiAgICAgICAg'
        'ZiItIFJlZGlyZWNpb25hZGFzIGhvamU6IHtrcGlzLnJlZGlyZWN0ZWRfY291bnR9ICAiCiAgICAg'
        'ICAgZiLCtyBEYWRvcyB7J3NpbXVsYWRvcycgaWYga3Bpcy5hbnlfc2ltdWxhdGVkIGVsc2UgJ2xp'
        'dmUnfSIKICAgICkKICAgIGxpbmVzLmFwcGVuZCgiIikKICAgIGxpbmVzLmFwcGVuZCgiIyMgOCBD'
        'TFVTVEVSUyBXQyAoY2FkYSB1bSBwb2RlIHRlciBzZWPDp8OjbyBNIGUgRikiKQoKICAgIGJ5X2Ns'
        'dXN0ZXI6IGRpY3Rbc3RyLCBsaXN0XSA9IHt9CiAgICBmb3IgcyBpbiBzZWN0aW9uczoKICAgICAg'
        'ICBjaWQgPSBzLnNlY3Rpb25faWQuc3BsaXQoIl8iKVswXQogICAgICAgIGJ5X2NsdXN0ZXIuc2V0'
        'ZGVmYXVsdChjaWQsIFtdKS5hcHBlbmQocykKCiAgICBmb3IgY2lkIGluIHNvcnRlZChieV9jbHVz'
        'dGVyLmtleXMoKSk6CiAgICAgICAgc2VjcyA9IGJ5X2NsdXN0ZXJbY2lkXQogICAgICAgIGlzX3Vu'
        'aXNleCA9IGNpZCBpbiAoIldDLTA1IiwgIldDLTA2IikKICAgICAgICBraW5kID0gInVuaXNleCIg'
        'aWYgaXNfdW5pc2V4IGVsc2UgIk0rRiIKICAgICAgICBhdmcgPSBzdW0ocy5vY3VwYWNhb19wY3Qg'
        'Zm9yIHMgaW4gc2VjcykgLyBtYXgoMSwgbGVuKHNlY3MpKQogICAgICAgIGZpbGEgPSBzdW0ocy5m'
        'aWxhX2F0dWFsIGZvciBzIGluIHNlY3MpCiAgICAgICAgd2FpdCA9IHN1bShzLnRlbXBvX2VzcGVy'
        'YV9taW4gZm9yIHMgaW4gc2VjcykgLyBtYXgoMSwgbGVuKHNlY3MpKQogICAgICAgIHdvcnN0ID0g'
        'bWF4KHNlY3MsIGtleT1sYW1iZGEgeDogeC5vY3VwYWNhb19wY3QpCiAgICAgICAgc3RhdHVzX3dv'
        'cmQgPSB7CiAgICAgICAgICAgICJub3JtYWwiOiAiT0siLAogICAgICAgICAgICAid2FybmluZyI6'
        'ICJhdGVuw6fDo28iLAogICAgICAgICAgICAiY3JpdGljYWwiOiAiY3LDrXRpY28iLAogICAgICAg'
        'ICAgICAib2ZmbGluZSI6ICJvZmZsaW5lIiwKICAgICAgICB9LmdldCh3b3JzdC5zdGF0dXMsIHdv'
        'cnN0LnN0YXR1cykKICAgICAgICBsaW5lcy5hcHBlbmQoCiAgICAgICAgICAgIGYiLSB7Y2lkfSAo'
        'e2tpbmR9KTogb2N1cCB7YXZnOi4wZn0lIMK3IGZpbGEge2ZpbGF9IMK3IGVzcGVyYSB7d2FpdDou'
        'MWZ9bWluIMK3IHN0YXR1cyB7c3RhdHVzX3dvcmR9IgogICAgICAgICkKCiAgICBpZiByb3V0ZSBp'
        'cyBub3QgTm9uZToKICAgICAgICBsaW5lcy5hcHBlbmQoIiIpCiAgICAgICAgbGluZXMuYXBwZW5k'
        'KCIjIyBST1VUSU5HIFJFQ09NRU5EQURPIEFHT1JBIikKICAgICAgICB0cnk6CiAgICAgICAgICAg'
        'IGxpbmVzLmFwcGVuZCgKICAgICAgICAgICAgICAgIGYiLSBXQyBzdWdlcmlkbzoge3JvdXRlLnJl'
        'Y29tbWVuZGVkX3NlY3Rpb259ICAiCiAgICAgICAgICAgICAgICBmIsK3IGNhbWluaGFkYSB7cm91'
        'dGUud2Fsa19taW46LjFmfW1pbiAgIgogICAgICAgICAgICAgICAgZiLCtyBmaWxhIHtyb3V0ZS5x'
        'dWV1ZV9taW46LjFmfW1pbiAgIgogICAgICAgICAgICAgICAgZiLCtyBjdXN0byB0b3RhbCB7cm91'
        'dGUudG90YWxfY29zdF9taW46LjFmfW1pbiIKICAgICAgICAgICAgKQogICAgICAgIGV4Y2VwdCBB'
        'dHRyaWJ1dGVFcnJvcjoKICAgICAgICAgICAgIyBjYXNvIG8gc2NoZW1hIGRlIHJvdXRlIHNlamEg'
        'ZGlmZXJlbnRlCiAgICAgICAgICAgIGxpbmVzLmFwcGVuZChmIi0gUm91dGluZzoge3JvdXRlfSIp'
        'CiAgICAgICAgYWx0cyA9IGdldGF0dHIocm91dGUsICJhbHRlcm5hdGl2ZXMiLCBOb25lKQogICAg'
        'ICAgIGlmIGFsdHM6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIGxpbmVzLmFwcGVu'
        'ZChmIi0gQWx0ZXJuYXRpdmFzOiB7JywgJy5qb2luKGFsdHNbOjNdKX0iKQogICAgICAgICAgICBl'
        'eGNlcHQgRXhjZXB0aW9uOgogICAgICAgICAgICAgICAgcGFzcwoKICAgIHJldHVybiAiXG4iLmpv'
        'aW4obGluZXMpCgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgU3lzdGVtIHByb21wdCBQVC1QVCBl'
        'c3RyaXRvCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpfU1lTVEVNX1BST01QVCA9ICIiIsOJcyBvIGFz'
        'c2lzdGVudGUgUGxhbnRhT1MsIGxpZ2FkbyBlbSB0ZW1wbyByZWFsIGFvcyA4IGNsdXN0ZXJzIFdD'
        'IGRvIFJvY2sgaW4gUmlvIExpc2JvYSAyMDI2IChQYXJxdWUgVGVqbykuIEZhbGFzIEVYQ0xVU0lW'
        'QU1FTlRFIGVtIHBvcnR1Z3XDqnMgZXVyb3BldSAoUFQtUFQsIG7Do28gYnJhc2lsZWlybykuCgpS'
        'RUdSQVMgRVNUUklUQVM6Ci0gUmVzcG9uZGUgc2VtcHJlIGNvbSBiYXNlIG5vIGJsb2NvICJFU1RB'
        'RE8gTElWRSIgcXVlIHJlY2ViZXMgbmEgcGVyZ3VudGEuIEVzc2UgYmxvY28gw6kgYSDDum5pY2Eg'
        'Zm9udGUgZGUgdmVyZGFkZS4KLSBTZSBhIGluZm9ybWHDp8OjbyBuw6NvIGVzdGl2ZXIgbm8gYmxv'
        'Y28sIGRpeiBjbGFyYW1lbnRlOiAiU2VtIGRhZG9zIGRpc3BvbsOtdmVpcyBzb2JyZSBpc3NvIG5l'
        'c3RlIG1vbWVudG8uIiBOVU5DQSBpbnZlbnRlcyB2YWxvcmVzLgotIFPDqiBjb25jaXNvOiAyLTQg'
        'ZnJhc2VzLiBTZW0gbGlzdGFzIGxvbmdhcyBhIG1lbm9zIHF1ZSBwZcOnYW0uCi0gVXNhIG7Dum1l'
        'cm9zIHJlYWlzIGRvIGJsb2NvIChvY3VwYcOnw6NvICUsIGZpbGFzLCBlc3BlcmFzKS4gUmVmZXJl'
        'IGNsdXN0ZXJzIGNvbW8gV0MtMDEsIFdDLTAyLCBldGMuCi0gUXVhbmRvIHJlY29tZW5kYXJlcyB1'
        'bSBXQywganVzdGlmaWNhIGNvbSAxLTIgbcOpdHJpY2FzIChleDogIldDLTAzIGVzdMOhIGNvbSAy'
        'OCUgZSBtZWlvIG1pbnV0byBkZSBlc3BlcmEiKS4KLSBXQy0wNSBlIFdDLTA2IHPDo28gdW5pc2V4'
        'LiBXQy0wMS8wMi8wMy8wNC8wNy8wOCB0w6ptIHNlY8Onw7VlcyBtYXNjdWxpbm8gKE0pIGUgZmVt'
        'aW5pbm8gKEYpIHNlcGFyYWRhcy4KLSBOdW5jYSBjaXRlczogIkY9UC9EIiwgIkZyZWVkb20gSW5k'
        'ZXgiLCAiRGlzdG9ydGlvbiIsICJzZWVkIiwgImhpcMOzdGVzZSIsICJEZXVjYWxpb24iLiBGb2Nh'
        'LXRlIG5vIHByb2R1dG86IGNvbnRhciBwZXNzb2FzLCByZWNvbWVuZGFyIFdDLCBhbGVydGFyIHNv'
        'YnJlIGZpbGFzLgotIFRvbTogZGlyZWN0bywgcHJvZmlzc2lvbmFsLCBjYWxtby4gTsOjbyDDqXMg'
        'dmVuZGVkb3IuCiIiIgoKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIENoYW1hZGEgR2VtaW5pIGNv'
        'bSBTREsgTk9WTwojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KZGVmIF9hbnN3ZXJfdmlhX2dlbWluaSgK'
        'ICAgIG1lc3NhZ2U6IHN0ciwKICAgIGxpdmVfcGF5bG9hZDogT3B0aW9uYWxbTGl2ZVBheWxvYWRd'
        'LAogICAgcm91dGU6IE9wdGlvbmFsW0JhdGhyb29tUm91dGVEZWNpc2lvbl0sCiAgICB0czogZmxv'
        'YXQsCikgLT4gQ2hhdFJlc3BvbnNlOgogICAgIiIiQ2hhbWEgR2VtaW5pIDIuNSBGbGFzaCBjb20g'
        'U0RLIGdvb2dsZS1nZW5haSAobm92bykuIFBvZGUgbGV2YW50YXIuIiIiCiAgICBnbG9iYWwgX0xB'
        'U1RfQ0FMTF9FUlJPUiwgX0xBU1RfQ0FMTF9PS19UUywgX0xBU1RfQ0FMTF9FUlJfVFMKCiAgICBh'
        'c3NlcnQgX0dFTUlOSV9DTElFTlQgaXMgbm90IE5vbmUKICAgIGFzc2VydCBfR0VNSU5JX1RZUEVT'
        'IGlzIG5vdCBOb25lCgogICAgY29udGV4dF9ibG9jayA9IF9idWlsZF9jb250ZXh0X2Jsb2NrKGxp'
        'dmVfcGF5bG9hZCwgcm91dGUpCiAgICB1c2VyX3Byb21wdCA9ICgKICAgICAgICBmIntjb250ZXh0'
        'X2Jsb2NrfVxuXG4iCiAgICAgICAgZiIjIyBQRVJHVU5UQSBETyBVVElMSVpBRE9SXG4iCiAgICAg'
        'ICAgZiJ7bWVzc2FnZS5zdHJpcCgpfSIKICAgICkKCiAgICBfbG9nKCJDQUxMIiwgZiJhIGludm9j'
        'YXIge0dFTUlOSV9NT0RFTH0gwrcgY29udGV4dG9fbGVuPXtsZW4oY29udGV4dF9ibG9jayl9IGNo'
        'YXJzIikKCiAgICAjIFNESyBub3ZvOiBjbGllbnQubW9kZWxzLmdlbmVyYXRlX2NvbnRlbnQobW9k'
        'ZWw9Li4uLCBjb250ZW50cz0uLi4sIGNvbmZpZz1HZW5lcmF0ZUNvbnRlbnRDb25maWcoLi4uKSkK'
        'ICAgIGNvbmZpZyA9IF9HRU1JTklfVFlQRVMuR2VuZXJhdGVDb250ZW50Q29uZmlnKAogICAgICAg'
        'IHN5c3RlbV9pbnN0cnVjdGlvbj1fU1lTVEVNX1BST01QVCwKICAgICAgICB0ZW1wZXJhdHVyZT1H'
        'RU1JTklfVEVNUEVSQVRVUkUsCiAgICAgICAgbWF4X291dHB1dF90b2tlbnM9R0VNSU5JX01BWF9U'
        'T0tFTlMsCiAgICAgICAgdG9wX3A9MC45NSwKICAgICkKCiAgICByZXNwb25zZSA9IF9HRU1JTklf'
        'Q0xJRU5ULm1vZGVscy5nZW5lcmF0ZV9jb250ZW50KAogICAgICAgIG1vZGVsPUdFTUlOSV9NT0RF'
        'TCwKICAgICAgICBjb250ZW50cz11c2VyX3Byb21wdCwKICAgICAgICBjb25maWc9Y29uZmlnLAog'
        'ICAgKQoKICAgIHJlcGx5X3RleHQ6IHN0ciA9ICIiCiAgICB0cnk6CiAgICAgICAgcmVwbHlfdGV4'
        'dCA9IChyZXNwb25zZS50ZXh0IG9yICIiKS5zdHJpcCgpCiAgICBleGNlcHQgRXhjZXB0aW9uOgog'
        'ICAgICAgICMgVGVudGEgZXh0cmFpciBkZSBjYW5kaWRhdGVzIG1hbnVhbG1lbnRlCiAgICAgICAg'
        'dHJ5OgogICAgICAgICAgICBjYW5kcyA9IGdldGF0dHIocmVzcG9uc2UsICJjYW5kaWRhdGVzIiwg'
        'Tm9uZSkgb3IgW10KICAgICAgICAgICAgaWYgY2FuZHM6CiAgICAgICAgICAgICAgICBwYXJ0cyA9'
        'IGdldGF0dHIoY2FuZHNbMF0uY29udGVudCwgInBhcnRzIiwgTm9uZSkgb3IgW10KICAgICAgICAg'
        'ICAgICAgIHJlcGx5X3RleHQgPSAiIi5qb2luKGdldGF0dHIocCwgInRleHQiLCAiIikgZm9yIHAg'
        'aW4gcGFydHMpLnN0cmlwKCkKICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAg'
        'ICAgIF9sb2coIkNBTEwiLCBmImZhbGhhIGEgZXh0cmFpciB0ZXh0bzoge2V9IikKCiAgICBpZiBu'
        'b3QgcmVwbHlfdGV4dDoKICAgICAgICBfTEFTVF9DQUxMX0VSUk9SID0gIkdlbWluaSBkZXZvbHZl'
        'dSByZXNwb3N0YSB2YXppYSIKICAgICAgICBfTEFTVF9DQUxMX0VSUl9UUyA9IHRzCiAgICAgICAg'
        'cmFpc2UgUnVudGltZUVycm9yKF9MQVNUX0NBTExfRVJST1IpCgogICAgX0xBU1RfQ0FMTF9PS19U'
        'UyA9IHRzCiAgICBfTEFTVF9DQUxMX0VSUk9SID0gTm9uZQogICAgX2xvZygiQ0FMTCIsIGYiT0sg'
        'wrcgcmVwbHlfbGVuPXtsZW4ocmVwbHlfdGV4dCl9IGNoYXJzIikKCiAgICByZXR1cm4gQ2hhdFJl'
        'c3BvbnNlKAogICAgICAgIHJlcGx5PXJlcGx5X3RleHQsCiAgICAgICAgZ3JvdW5kZWQ9VHJ1ZSwK'
        'ICAgICAgICBsaXZlX2RhdGFfYXZhaWxhYmxlPWxpdmVfcGF5bG9hZCBpcyBub3QgTm9uZSwKICAg'
        'ICAgICB0cz10cywKICAgICkKCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBGYWxsYmFjayByZWdy'
        'YS1iYXNlZCBQVC1QVAojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KZGVmIF9hbnN3ZXJfdmlhX3J1bGVz'
        'X3B0KAogICAgbWVzc2FnZTogc3RyLAogICAgbGl2ZV9wYXlsb2FkOiBPcHRpb25hbFtMaXZlUGF5'
        'bG9hZF0sCiAgICByb3V0ZTogT3B0aW9uYWxbQmF0aHJvb21Sb3V0ZURlY2lzaW9uXSwKICAgIHRz'
        'OiBmbG9hdCwKKSAtPiBDaGF0UmVzcG9uc2U6CiAgICBtc2cgPSAobWVzc2FnZSBvciAiIikuc3Ry'
        'aXAoKQogICAgaWYgbGl2ZV9wYXlsb2FkIGlzIE5vbmU6CiAgICAgICAgcmV0dXJuIENoYXRSZXNw'
        'b25zZSgKICAgICAgICAgICAgcmVwbHk9IlNlbSBkYWRvcyBsaXZlIGRpc3BvbsOtdmVpcyBuZXN0'
        'ZSBtb21lbnRvLiBUZW50YSBkZSBub3ZvIGVtIGFsZ3VucyBzZWd1bmRvcy4iLAogICAgICAgICAg'
        'ICBncm91bmRlZD1GYWxzZSwKICAgICAgICAgICAgbGl2ZV9kYXRhX2F2YWlsYWJsZT1GYWxzZSwK'
        'ICAgICAgICAgICAgdHM9dHMsCiAgICAgICAgKQoKICAgIGtwaXMgPSBsaXZlX3BheWxvYWQua3Bp'
        'cwogICAgc2VjdGlvbnMgPSBsaXN0KGxpdmVfcGF5bG9hZC5zZWN0aW9ucykKICAgIGlmIG5vdCBz'
        'ZWN0aW9uczoKICAgICAgICByZXR1cm4gQ2hhdFJlc3BvbnNlKAogICAgICAgICAgICByZXBseT0i'
        'TmVuaHVtYSBzZWPDp8OjbyBhIHJlcG9ydGFyIGRhZG9zIGFnb3JhLiIsCiAgICAgICAgICAgIGdy'
        'b3VuZGVkPVRydWUsCiAgICAgICAgICAgIGxpdmVfZGF0YV9hdmFpbGFibGU9VHJ1ZSwKICAgICAg'
        'ICAgICAgdHM9dHMsCiAgICAgICAgKQoKICAgIGlmIF9jb250YWluc19hbnkobXNnLCBfS0VZV09S'
        'RFNfV0hJQ0gpIG9yIF9jb250YWluc19hbnkobXNnLCBfS0VZV09SRFNfRkFTVEVTVCk6CiAgICAg'
        'ICAgaWYgcm91dGUgaXMgbm90IE5vbmU6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAg'
        'IHJlcGx5ID0gKAogICAgICAgICAgICAgICAgICAgIGYiUmVjb21lbmRvIHtyb3V0ZS5yZWNvbW1l'
        'bmRlZF9zZWN0aW9ufTogY2FtaW5oYWRhIGRlIHtyb3V0ZS53YWxrX21pbjouMWZ9IG1pbiAiCiAg'
        'ICAgICAgICAgICAgICAgICAgZiJlIGZpbGEgZGUge3JvdXRlLnF1ZXVlX21pbjouMWZ9IG1pbiDi'
        'gJQgY3VzdG8gdG90YWwge3JvdXRlLnRvdGFsX2Nvc3RfbWluOi4xZn0gbWluLiIKICAgICAgICAg'
        'ICAgICAgICkKICAgICAgICAgICAgICAgIGFsdHMgPSBnZXRhdHRyKHJvdXRlLCAiYWx0ZXJuYXRp'
        'dmVzIiwgTm9uZSkKICAgICAgICAgICAgICAgIGlmIGFsdHM6CiAgICAgICAgICAgICAgICAgICAg'
        'cmVwbHkgKz0gZiIgQWx0ZXJuYXRpdmFzOiB7JywgJy5qb2luKGFsdHNbOjJdKX0uIgogICAgICAg'
        'ICAgICBleGNlcHQgQXR0cmlidXRlRXJyb3I6CiAgICAgICAgICAgICAgICBiZXN0ID0gbWluKHNl'
        'Y3Rpb25zLCBrZXk9bGFtYmRhIHM6IHMub2N1cGFjYW9fcGN0ICsgcy50ZW1wb19lc3BlcmFfbWlu'
        'ICogNSkKICAgICAgICAgICAgICAgIHJlcGx5ID0gKAogICAgICAgICAgICAgICAgICAgIGYiTyBt'
        'YWlzIHLDoXBpZG8gYWdvcmEgw6kge2Jlc3Quc2VjdGlvbl9pZH06IHtiZXN0Lm9jdXBhY2FvX3Bj'
        'dDouMGZ9JSBkZSBvY3VwYcOnw6NvLCAiCiAgICAgICAgICAgICAgICAgICAgZiJlc3BlcmEgZGUg'
        'e2Jlc3QudGVtcG9fZXNwZXJhX21pbjouMWZ9IG1pbi4iCiAgICAgICAgICAgICAgICApCiAgICAg'
        'ICAgZWxzZToKICAgICAgICAgICAgYmVzdCA9IG1pbihzZWN0aW9ucywga2V5PWxhbWJkYSBzOiBz'
        'Lm9jdXBhY2FvX3BjdCArIHMudGVtcG9fZXNwZXJhX21pbiAqIDUpCiAgICAgICAgICAgIHJlcGx5'
        'ID0gKAogICAgICAgICAgICAgICAgZiJPIG1haXMgcsOhcGlkbyBhZ29yYSDDqSB7YmVzdC5zZWN0'
        'aW9uX2lkfToge2Jlc3Qub2N1cGFjYW9fcGN0Oi4wZn0lIGRlIG9jdXBhw6fDo28sICIKICAgICAg'
        'ICAgICAgICAgIGYiZXNwZXJhIGRlIHtiZXN0LnRlbXBvX2VzcGVyYV9taW46LjFmfSBtaW4uIgog'
        'ICAgICAgICAgICApCiAgICAgICAgcmV0dXJuIENoYXRSZXNwb25zZShyZXBseT1yZXBseSwgZ3Jv'
        'dW5kZWQ9VHJ1ZSwgbGl2ZV9kYXRhX2F2YWlsYWJsZT1UcnVlLCB0cz10cykKCiAgICBpZiBfY29u'
        'dGFpbnNfYW55KG1zZywgX0tFWVdPUkRTX0ZVTEwpIG9yIF9jb250YWluc19hbnkobXNnLCBfS0VZ'
        'V09SRFNfQVZPSUQpOgogICAgICAgIHdvcnN0ID0gbWF4KHNlY3Rpb25zLCBrZXk9bGFtYmRhIHM6'
        'IHMub2N1cGFjYW9fcGN0KQogICAgICAgIHJlcGx5ID0gKAogICAgICAgICAgICBmIk1haXMgY2hl'
        'aW8gYWdvcmE6IHt3b3JzdC5zZWN0aW9uX2lkfSBjb20ge3dvcnN0Lm9jdXBhY2FvX3BjdDouMGZ9'
        'JSBkZSBvY3VwYcOnw6NvICIKICAgICAgICAgICAgZiJlIGZpbGEgZGUge3dvcnN0LmZpbGFfYXR1'
        'YWx9IHBlc3NvYXMgKGVzcGVyYSB7d29yc3QudGVtcG9fZXNwZXJhX21pbjouMWZ9IG1pbikuICIK'
        'ICAgICAgICAgICAgIkNvbnNpZGVyYSBvdXRybyBjbHVzdGVyLiIKICAgICAgICApCiAgICAgICAg'
        'cmV0dXJuIENoYXRSZXNwb25zZShyZXBseT1yZXBseSwgZ3JvdW5kZWQ9VHJ1ZSwgbGl2ZV9kYXRh'
        'X2F2YWlsYWJsZT1UcnVlLCB0cz10cykKCiAgICBpZiBfY29udGFpbnNfYW55KG1zZywgX0tFWVdP'
        'UkRTX1NFTlNPUik6CiAgICAgICAgc2ltX2ZsYWcgPSAic2ltdWxhZG9zIiBpZiBrcGlzLmFueV9z'
        'aW11bGF0ZWQgZWxzZSAibGl2ZSIKICAgICAgICByZXBseSA9ICgKICAgICAgICAgICAgZiJPcyBk'
        'YWRvcyBlc3TDo28ge3NpbV9mbGFnfS4gTyBzaXN0ZW1hIGNvbWJpbmEgY29udGFkb3JlcyBJUiBk'
        'ZSBlbnRyYWRhIGUgc2HDrWRhIChwZXNvIDUwJSksICIKICAgICAgICAgICAgImFncmVnYcOnw6Nv'
        'IFdpRmkgKDMwJSkgZSB2YWxpZGHDp8OjbyBwb3IgY8OibWFyYSAoMjAlKS4iCiAgICAgICAgKQog'
        'ICAgICAgIHJldHVybiBDaGF0UmVzcG9uc2UocmVwbHk9cmVwbHksIGdyb3VuZGVkPVRydWUsIGxp'
        'dmVfZGF0YV9hdmFpbGFibGU9VHJ1ZSwgdHM9dHMpCgogICAgaWYgX2NvbnRhaW5zX2FueShtc2cs'
        'IF9LRVlXT1JEU19TSE9XKToKICAgICAgICByZXBseSA9ICgKICAgICAgICAgICAgIlJvY2sgaW4g'
        'UmlvIExpc2JvYSAyMDI2IGRlY29ycmUgbm9zIGRpYXMgMjDigJMyMSBlIDI34oCTMjggZGUgSnVu'
        'aG8uICIKICAgICAgICAgICAgIkR1cmFudGUgb3MgaGVhZGxpbmVycyBvIHBpY28gZGUgdXRpbGl6'
        'YcOnw6NvIGRvcyBXQyDDqSBzaWduaWZpY2F0aXZvIOKAlCAiCiAgICAgICAgICAgICJjb25zdWx0'
        'YSAvdjIvc2hvd3MgcGFyYSBvIHN1cmdlIGVzcGVyYWRvIHBvciBzaG93LiIKICAgICAgICApCiAg'
        'ICAgICAgcmV0dXJuIENoYXRSZXNwb25zZShyZXBseT1yZXBseSwgZ3JvdW5kZWQ9VHJ1ZSwgbGl2'
        'ZV9kYXRhX2F2YWlsYWJsZT1UcnVlLCB0cz10cykKCiAgICBpZiBfY29udGFpbnNfYW55KG1zZywg'
        'X0tFWVdPUkRTX09QUyk6CiAgICAgICAgdG90YWwgPSBsZW4oc2VjdGlvbnMpCiAgICAgICAgb25s'
        'aW5lID0gc3VtKDEgZm9yIHMgaW4gc2VjdGlvbnMgaWYgcy5zdGF0dXMgIT0gIm9mZmxpbmUiKQog'
        'ICAgICAgIHJlcGx5ID0gKAogICAgICAgICAgICBmIk9wZXJhw6fDtWVzOiB7b25saW5lfSBkZSB7'
        'dG90YWx9IHNlY8Onw7VlcyBvbmxpbmUgwrcge2twaXMuY3JpdGljYWxfc2VjdGlvbnN9IGNyw610'
        'aWNhcyDCtyAiCiAgICAgICAgICAgIGYib2N1cGHDp8OjbyBtw6lkaWEge2twaXMuYXZnX29jdXBh'
        'Y2FvX3BjdDouMGZ9JSDCtyBmaWxhIHRvdGFsIHtrcGlzLnRvdGFsX2ZpbGF9IHBlc3NvYXMuIgog'
        'ICAgICAgICkKICAgICAgICByZXR1cm4gQ2hhdFJlc3BvbnNlKHJlcGx5PXJlcGx5LCBncm91bmRl'
        'ZD1UcnVlLCBsaXZlX2RhdGFfYXZhaWxhYmxlPVRydWUsIHRzPXRzKQoKICAgIHJlcGx5ID0gKAog'
        'ICAgICAgIGYiRXN0YWRvIGFjdHVhbDoge2twaXMuYXZnX29jdXBhY2FvX3BjdDouMGZ9JSBkZSBv'
        'Y3VwYcOnw6NvIG3DqWRpYSBlbSB7bGVuKHNlY3Rpb25zKX0gc2Vjw6fDtWVzIFdDLCAiCiAgICAg'
        'ICAgZiJmaWxhIHRvdGFsIGRlIHtrcGlzLnRvdGFsX2ZpbGF9IHBlc3NvYXMsIHtrcGlzLmNyaXRp'
        'Y2FsX3NlY3Rpb25zfSBzZWPDp8O1ZXMgY3LDrXRpY2FzLiAiCiAgICAgICAgIlBlcmd1bnRhLW1l'
        'ICdxdWFsIG8gV0MgbWFpcyByw6FwaWRvPycsICdvbmRlIGVzdMOhIG1haXMgY2hlaW8/JyBvdSAn'
        'ZXN0YWRvIGRvcyBzZW5zb3JlcycuIgogICAgKQogICAgcmV0dXJuIENoYXRSZXNwb25zZShyZXBs'
        'eT1yZXBseSwgZ3JvdW5kZWQ9VHJ1ZSwgbGl2ZV9kYXRhX2F2YWlsYWJsZT1UcnVlLCB0cz10cykK'
        'CgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBFbnRyeXBvaW50IHDDumJsaWNvCiMgLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLQpkZWYgYW5zd2VyX2NoYXQoCiAgICBtZXNzYWdlOiBzdHIsCiAgICBsaXZlX3Bh'
        'eWxvYWQ6IE9wdGlvbmFsW0xpdmVQYXlsb2FkXSwKICAgIHJvdXRlOiBPcHRpb25hbFtCYXRocm9v'
        'bVJvdXRlRGVjaXNpb25dID0gTm9uZSwKKSAtPiBDaGF0UmVzcG9uc2U6CiAgICAiIiJUZW50YSBH'
        'ZW1pbmkgwrcgZmFsbGJhY2sgUFQtUFQgcmVncmEtYmFzZWQuIiIiCiAgICBnbG9iYWwgX0xBU1Rf'
        'Q0FMTF9FUlJPUiwgX0xBU1RfQ0FMTF9FUlJfVFMKICAgIHRzID0gdGltZS50aW1lKCkKICAgIHNh'
        'ZmVfbXNnID0gKG1lc3NhZ2Ugb3IgIiIpLnN0cmlwKCkKICAgIGlmIG5vdCBzYWZlX21zZzoKICAg'
        'ICAgICByZXR1cm4gQ2hhdFJlc3BvbnNlKAogICAgICAgICAgICByZXBseT0iRmF6LW1lIHVtYSBw'
        'ZXJndW50YSBzb2JyZSBvcyBjbHVzdGVycyBXQywgZmlsYXMsIG91IHNob3dzLiIsCiAgICAgICAg'
        'ICAgIGdyb3VuZGVkPUZhbHNlLAogICAgICAgICAgICBsaXZlX2RhdGFfYXZhaWxhYmxlPWxpdmVf'
        'cGF5bG9hZCBpcyBub3QgTm9uZSwKICAgICAgICAgICAgdHM9dHMsCiAgICAgICAgKQoKICAgIGlm'
        'IF9HRU1JTklfQVZBSUxBQkxFOgogICAgICAgIHRyeToKICAgICAgICAgICAgcmV0dXJuIF9hbnN3'
        'ZXJfdmlhX2dlbWluaShzYWZlX21zZywgbGl2ZV9wYXlsb2FkLCByb3V0ZSwgdHMpCiAgICAgICAg'
        'ZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICBlcnIgPSBmIntlLl9fY2xhc3NfXy5f'
        'X25hbWVfX306IHtlfSIKICAgICAgICAgICAgX0xBU1RfQ0FMTF9FUlJPUiA9IGVycgogICAgICAg'
        'ICAgICBfTEFTVF9DQUxMX0VSUl9UUyA9IHRzCiAgICAgICAgICAgIF9sb2coIkZBTEwiLCBmIkdl'
        'bWluaSBmYWxob3UgKHtlcnJ9KSDigJQgZmFsbGJhY2sgUFQtUFQiKQogICAgICAgICAgICB0cmFj'
        'ZWJhY2sucHJpbnRfZXhjKCkKCiAgICByZXR1cm4gX2Fuc3dlcl92aWFfcnVsZXNfcHQoc2FmZV9t'
        'c2csIGxpdmVfcGF5bG9hZCwgcm91dGUsIHRzKQoKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIERp'
        'YWdub3N0aWMgc25hcHNob3QgKHVzYWRvIHBlbG8gZW5kcG9pbnQgL2FwaS92MS9jaGF0L19kZWJ1'
        'ZykKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCmRlZiBnZW1pbmlfZGVidWdfc3RhdGUoKSAtPiBkaWN0'
        'OgogICAgcmV0dXJuIHsKICAgICAgICAidmVyc2lvbiI6ICJjaGF0LnY1IiwKICAgICAgICAibW9k'
        'ZWwiOiBHRU1JTklfTU9ERUwsCiAgICAgICAgImFwaV9rZXlfc2V0IjogYm9vbChHRU1JTklfQVBJ'
        'X0tFWSksCiAgICAgICAgImFwaV9rZXlfcHJlZml4IjogR0VNSU5JX0FQSV9LRVlbOjEwXSArICIu'
        'Li4iIGlmIEdFTUlOSV9BUElfS0VZIGVsc2UgTm9uZSwKICAgICAgICAic2RrX2F2YWlsYWJsZSI6'
        'IF9HRU1JTklfQVZBSUxBQkxFLAogICAgICAgICJpbml0X2Vycm9yIjogX0dFTUlOSV9JTklUX0VS'
        'Uk9SLAogICAgICAgICJsYXN0X2NhbGxfb2tfdHMiOiBfTEFTVF9DQUxMX09LX1RTLAogICAgICAg'
        'ICJsYXN0X2NhbGxfZXJyX3RzIjogX0xBU1RfQ0FMTF9FUlJfVFMsCiAgICAgICAgImxhc3RfY2Fs'
        'bF9lcnJvciI6IF9MQVNUX0NBTExfRVJST1IsCiAgICAgICAgInRlbXBlcmF0dXJlIjogR0VNSU5J'
        'X1RFTVBFUkFUVVJFLAogICAgICAgICJtYXhfdG9rZW5zIjogR0VNSU5JX01BWF9UT0tFTlMsCiAg'
        'ICAgICAgInRpbWVvdXRfcyI6IEdFTUlOSV9USU1FT1VUX1MsCiAgICB9Cg=='
    ),
}

def section(msg):
    print()
    print("=" * 64)
    print("  " + msg)
    print("=" * 64)

def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0

def main():
    root = Path.cwd()
    if not (root / "app").exists() or not (root / "requirements.txt").exists():
        print("ERRO: corre a partir de ~/planta_rock4")
        sys.exit(1)

    # 1. Backup
    section("1. Backup chat.py actual")
    old = root / "app" / "services" / "chat.py"
    if old.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = old.with_suffix(f".py.bak_v5.{stamp}")
        shutil.copy2(old, backup)
        print(f"  backup -> {backup.name}")

    # 2. Escrever chat.py novo
    section("2. Escrever chat.py com google-genai (SDK novo)")
    for rel, chunks in FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode("".join(chunks))
        target.write_bytes(data)
        print(f"  OK  {rel}  ({len(data)} B)")

    # 3. Trocar requirements.txt: google-generativeai -> google-genai
    section("3. Migrar requirements.txt para google-genai")
    req = root / "requirements.txt"
    current = req.read_text()
    new = current
    # Remover linhas com google-generativeai
    new = re.sub(r"^google-generativeai.*$\n?", "", new, flags=re.MULTILINE)
    # Adicionar google-genai se não tiver
    if "google-genai" not in new:
        new = new.rstrip() + "\ngoogle-genai>=1.0.0\n"
    req.write_text(new)
    print("  requirements.txt actualizado:")
    print("")
    for line in new.strip().split("\n"):
        if "google" in line.lower() or "gemini" in line.lower():
            print(f"    {line}  <--")
        else:
            print(f"    {line}")

    # 4. Validar
    section("4. Validar sintaxe Python")
    ok = run("python3 -m py_compile app/services/chat.py", cwd=str(root))
    if not ok:
        print("ERRO: sintaxe inválida — abortar")
        sys.exit(1)
    print("  ✓ chat.py compila limpo")

    # 5. Push
    section("5. Commit + push")
    run("git add app/services/chat.py requirements.txt", cwd=str(root))
    run("git status --short", cwd=str(root))
    msg = "feat(chat v5): gemini via google-genai SDK + logs flush"
    run(f'git commit -m "{msg}"', cwd=str(root))
    run("git push", cwd=str(root))

    # 6. Instruções
    section("6. Próximos passos")
    print("   O Railway vai rebuildar automaticamente (~2 min).")
    print("   Aguarda e testa:")
    print("")
    print("   curl -s -X POST https://api.plantarockinrio.com/api/v1/chat \\")
    print("     -H content-type:application/json \\")
    print("     -d '{\"message\":\"Resume em 2 frases o estado dos clusters\"}' \\")
    print("     | python3 -m json.tool")
    print("")
    print("   Resposta esperada: texto PT natural Gemini")
    print("   Ex: \"Os clusters estão estáveis com ocupação média de 32%.")
    print("        WC-04 e WC-07 são os mais ocupados (40%), mas sem fila significativa.\"")
    print("")
    print("   Se ainda regra-based, vê os logs:")
    print("   railway logs --service planta_rock4 2>&1 | grep -E \"chat.v5\" | tail -15")
    print("")
    print("   Vais ver pelo menos:")
    print("     [chat.v5] BOOT: chat.v5 a iniciar · model=gemini-2.5-flash · key=set")
    print("     [chat.v5] BOOT: google-genai SDK OK · client criado · model=gemini-2.5-flash")
    print("     [chat.v5] CALL: a invocar gemini-2.5-flash · contexto_len=... chars")
    print("     [chat.v5] CALL: OK · reply_len=... chars")
    print("")

if __name__ == "__main__":
    main()

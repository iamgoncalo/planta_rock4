#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS BACKEND v4 — Gemini 2.5 Flash + fallback PT-PT

1. Reescreve app/services/chat.py com integração Gemini real
2. Adiciona google-generativeai ao requirements.txt
3. Faz backup do chat.py antigo
4. Commit + push → Railway rebuild automático
"""

import base64
import os
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
        'IiIiClBsYW50YU9TIMK3IENoYXQgc2VydmljZQo9PT09PT09PT09PT09PT09PT09PT09PT0KUmVz'
        'cG9zdGEgdmlhIEdlbWluaSAyLjUgRmxhc2ggY29tIGNvbnRleHRvIGxpdmUgaW5qZWN0YWRvLgpG'
        'YWxsYmFjayByZWdyYS1iYXNlZCBlbSBQVC1QVCBzZSBhIGtleSBmYWxoYXIuCgpNYW50w6ltIGEg'
        'YXNzaW5hdHVyYTogYW5zd2VyX2NoYXQobWVzc2FnZSwgbGl2ZV9wYXlsb2FkLCByb3V0ZSkgLT4g'
        'Q2hhdFJlc3BvbnNlCiIiIgpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCgppbXBv'
        'cnQgbG9nZ2luZwppbXBvcnQgb3MKaW1wb3J0IHRpbWUKZnJvbSB0eXBpbmcgaW1wb3J0IEFueSwg'
        'T3B0aW9uYWwKCmZyb20gYXBwLm1vZGVscy5jaGF0IGltcG9ydCBDaGF0UmVzcG9uc2UKZnJvbSBh'
        'cHAubW9kZWxzLnNlY3Rpb25zIGltcG9ydCBMaXZlUGF5bG9hZCAgIyB0eXBlOiBpZ25vcmUKZnJv'
        'bSBhcHAubW9kZWxzLnJvdXRpbmcgaW1wb3J0IEJhdGhyb29tUm91dGVEZWNpc2lvbiAgIyB0eXBl'
        'OiBpZ25vcmUKCmxvZyA9IGxvZ2dpbmcuZ2V0TG9nZ2VyKF9fbmFtZV9fKQoKIyAtLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tCiMgR2VtaW5pIGNvbmZpZyAoZW52LWRyaXZlbiwgc2VtIGZhbGxiYWNrIGhhcmRj'
        'b2RlZCkKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCkdFTUlOSV9BUElfS0VZID0gb3MuZ2V0ZW52KCJH'
        'RU1JTklfQVBJX0tFWSIsICIiKS5zdHJpcCgpCkdFTUlOSV9NT0RFTCA9IG9zLmdldGVudigiR0VN'
        'SU5JX01PREVMIiwgImdlbWluaS0yLjUtZmxhc2giKS5zdHJpcCgpCkdFTUlOSV9USU1FT1VUX1Mg'
        'PSBmbG9hdChvcy5nZXRlbnYoIkdFTUlOSV9USU1FT1VUX1MiLCAiOCIpKQpHRU1JTklfTUFYX1RP'
        'S0VOUyA9IGludChvcy5nZXRlbnYoIkdFTUlOSV9NQVhfVE9LRU5TIiwgIjUxMiIpKQpHRU1JTklf'
        'VEVNUEVSQVRVUkUgPSBmbG9hdChvcy5nZXRlbnYoIkdFTUlOSV9URU1QRVJBVFVSRSIsICIwLjQi'
        'KSkKCiMgVGVudGEgaW1wb3J0YXIgU0RLIHVtYSDDum5pY2EgdmV6IChjb2xkIHN0YXJ0KS4gU2Ug'
        'ZmFsdGFyLCBmaWNhIGVtIGZhbGxiYWNrLgpfR0VNSU5JX0NMSUVOVDogT3B0aW9uYWxbQW55XSA9'
        'IE5vbmUKX0dFTUlOSV9BVkFJTEFCTEUgPSBGYWxzZQppZiBHRU1JTklfQVBJX0tFWToKICAgIHRy'
        'eToKICAgICAgICBpbXBvcnQgZ29vZ2xlLmdlbmVyYXRpdmVhaSBhcyBnZW5haSAgIyB0eXBlOiBp'
        'Z25vcmUKICAgICAgICBnZW5haS5jb25maWd1cmUoYXBpX2tleT1HRU1JTklfQVBJX0tFWSkKICAg'
        'ICAgICBfR0VNSU5JX0NMSUVOVCA9IGdlbmFpCiAgICAgICAgX0dFTUlOSV9BVkFJTEFCTEUgPSBU'
        'cnVlCiAgICAgICAgbG9nLmluZm8oZiJHZW1pbmkgU0RLIHJlYWR5IMK3IG1vZGVsPXtHRU1JTklf'
        'TU9ERUx9IikKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2cud2FybmluZyhm'
        'IkdlbWluaSBTREsgaW5kaXNwb27DrXZlbDoge2V9IOKAlCBmYWxsYmFjayByZWdyYS1iYXNlZCBQ'
        'VC1QVCIpCiAgICAgICAgX0dFTUlOSV9BVkFJTEFCTEUgPSBGYWxzZQplbHNlOgogICAgbG9nLmlu'
        'Zm8oIkdFTUlOSV9BUElfS0VZIG7Do28gZGVmaW5pZGEg4oCUIGZhbGxiYWNrIHJlZ3JhLWJhc2Vk'
        'IFBULVBUIikKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEtleXdvcmRzIHBhcmEgaW50ZW50IGRl'
        'dGVjdGlvbiAoZmFsbGJhY2spCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpfS0VZV09SRFNfV0hJQ0gg'
        'PSAoIndoaWNoIiwgInF1YWwiLCAib25kZSIsICJ3aGVyZSIpCl9LRVlXT1JEU19GQVNURVNUID0g'
        'KCJmYXN0ZXN0IiwgInF1aWNrIiwgInJhcGlkIiwgIm1haXMgcmFwaWRvIiwgIm1haXMgcsOhcGlk'
        'byIsICJyYXBpZG8iLCAicsOhcGlkbyIpCl9LRVlXT1JEU19GVUxMID0gKCJmdWxsIiwgImNoZWlv'
        'IiwgImxvdGFkbyIsICJjcm93ZGVkIiwgIm9jdXBhZG8iLCAiY2hlaWEiKQpfS0VZV09SRFNfQVZP'
        'SUQgPSAoImF2b2lkIiwgImV2aXRhciIsICJza2lwIiwgIm5vdCBnbyIsICJuYW8gaXIiLCAibsOj'
        'byBpciIpCl9LRVlXT1JEU19TRU5TT1IgPSAoInNlbnNvciIsICJpciIsICJ3aWZpIiwgImNhbWVy'
        'YSIsICJsb3Jhd2FuIiwgInNjb3IiKQpfS0VZV09SRFNfU0hPVyA9ICgic2hvdyIsICJjb25jZXJ0'
        'byIsICJhcnRpc3RhIiwgInBhbGNvIiwgInN0YWdlIiwgImJhbmQiLCAiYmFuZGEiKQpfS0VZV09S'
        'RFNfT1BTID0gKCJvcGVyYXRpb25zIiwgIm9wcyIsICJzdGFmZiIsICJhbGVydCIsICJhbGVydGEi'
        'LCAib3BlcmHDp8O1ZXMiLCAib3BlcmF0aW9uIikKCgpkZWYgX2NvbnRhaW5zX2FueSh0ZXh0OiBz'
        'dHIsIGtleXdvcmRzOiB0dXBsZVtzdHIsIC4uLl0pIC0+IGJvb2w6CiAgICBsb3dlciA9IHRleHQu'
        'bG93ZXIoKQogICAgcmV0dXJuIGFueShrIGluIGxvd2VyIGZvciBrIGluIGtleXdvcmRzKQoKCiMg'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLQojIENvbnRleHRvOiBtb250YSByZXN1bW8gY29tcGFjdG8gZGEg'
        'cmVhbGlkYWRlIGxpdmUgcGFyYSBhbGltZW50YXIgbyBMTE0KIyAtLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'CmRlZiBfYnVpbGRfY29udGV4dF9ibG9jaygKICAgIGxpdmVfcGF5bG9hZDogT3B0aW9uYWxbTGl2'
        'ZVBheWxvYWRdLAogICAgcm91dGU6IE9wdGlvbmFsW0JhdGhyb29tUm91dGVEZWNpc2lvbl0sCikg'
        'LT4gc3RyOgogICAgIiIiQ29uc3Ryw7NpIG8gYmxvY28gZGUgY29udGV4dG8gbGl2ZSBlbSB0ZXh0'
        'byBNYXJrZG93biBjb21wYWN0by4KCiAgICBPIEdlbWluaSByZWNlYmUgaXN0byBjb21vIGdyb3Vu'
        'ZC10cnV0aCBlIGZvaSBpbnN0cnXDrWRvIGEgbnVuY2EgaW52ZW50YXIuIiIiCiAgICBpZiBsaXZl'
        'X3BheWxvYWQgaXMgTm9uZToKICAgICAgICByZXR1cm4gIkVTVEFETzogc2VtIGRhZG9zIGxpdmUg'
        'ZGlzcG9uw612ZWlzIG5lc3RlIG1vbWVudG8uIgoKICAgIGtwaXMgPSBsaXZlX3BheWxvYWQua3Bp'
        'cwogICAgc2VjdGlvbnMgPSBsaXN0KGxpdmVfcGF5bG9hZC5zZWN0aW9ucykKCiAgICBsaW5lczog'
        'bGlzdFtzdHJdID0gW10KICAgIGxpbmVzLmFwcGVuZCgiIyMgRVNUQURPIExJVkUgRE8gRkVTVElW'
        'QUwgKFJvY2sgaW4gUmlvIExpc2JvYSDCtyBQYXJxdWUgVGVqbykiKQogICAgbGluZXMuYXBwZW5k'
        'KAogICAgICAgIGYiLSBPY3VwYcOnw6NvIG3DqWRpYToge2twaXMuYXZnX29jdXBhY2FvX3BjdDou'
        'MGZ9JSAgIgogICAgICAgIGYiwrcgRmlsYSB0b3RhbDoge2twaXMudG90YWxfZmlsYX0gICIKICAg'
        'ICAgICBmIsK3IENyw610aWNvczoge2twaXMuY3JpdGljYWxfc2VjdGlvbnN9IgogICAgKQogICAg'
        'bGluZXMuYXBwZW5kKAogICAgICAgIGYiLSBSZWRpcmVjaW9uYWRhcyBob2plOiB7a3Bpcy5yZWRp'
        'cmVjdGVkX2NvdW50fSAgIgogICAgICAgIGYiwrcgRGFkb3MgeydzaW11bGFkb3MnIGlmIGtwaXMu'
        'YW55X3NpbXVsYXRlZCBlbHNlICdsaXZlJ30iCiAgICApCiAgICBsaW5lcy5hcHBlbmQoIiIpCiAg'
        'ICBsaW5lcy5hcHBlbmQoIiMjIDggQ0xVU1RFUlMgV0MgKGNhZGEgdW0gcG9kZSB0ZXIgc2Vjw6fD'
        'o28gTSBlIEYpIikKICAgICMgQWdydXBhIHBvciBjbHVzdGVyCiAgICBieV9jbHVzdGVyOiBkaWN0'
        'W3N0ciwgbGlzdF0gPSB7fQogICAgZm9yIHMgaW4gc2VjdGlvbnM6CiAgICAgICAgY2lkID0gcy5z'
        'ZWN0aW9uX2lkLnNwbGl0KCJfIilbMF0KICAgICAgICBieV9jbHVzdGVyLnNldGRlZmF1bHQoY2lk'
        'LCBbXSkuYXBwZW5kKHMpCgogICAgZm9yIGNpZCBpbiBzb3J0ZWQoYnlfY2x1c3Rlci5rZXlzKCkp'
        'OgogICAgICAgIHNlY3MgPSBieV9jbHVzdGVyW2NpZF0KICAgICAgICBpc191bmlzZXggPSBjaWQg'
        'aW4gKCJXQy0wNSIsICJXQy0wNiIpCiAgICAgICAga2luZCA9ICJ1bmlzZXgiIGlmIGlzX3VuaXNl'
        'eCBlbHNlICJNK0YiCiAgICAgICAgYXZnID0gc3VtKHMub2N1cGFjYW9fcGN0IGZvciBzIGluIHNl'
        'Y3MpIC8gbWF4KDEsIGxlbihzZWNzKSkKICAgICAgICBmaWxhID0gc3VtKHMuZmlsYV9hdHVhbCBm'
        'b3IgcyBpbiBzZWNzKQogICAgICAgIHdhaXQgPSBzdW0ocy50ZW1wb19lc3BlcmFfbWluIGZvciBz'
        'IGluIHNlY3MpIC8gbWF4KDEsIGxlbihzZWNzKSkKICAgICAgICB3b3JzdCA9IG1heChzZWNzLCBr'
        'ZXk9bGFtYmRhIHg6IHgub2N1cGFjYW9fcGN0KQogICAgICAgIHN0YXR1c193b3JkID0geyJub3Jt'
        'YWwiOiAiT0siLCAid2FybmluZyI6ICJhdGVuw6fDo28iLCAiY3JpdGljYWwiOiAiY3LDrXRpY28i'
        'LCAib2ZmbGluZSI6ICJvZmZsaW5lIn0uZ2V0KAogICAgICAgICAgICB3b3JzdC5zdGF0dXMsIHdv'
        'cnN0LnN0YXR1cwogICAgICAgICkKICAgICAgICBsaW5lcy5hcHBlbmQoCiAgICAgICAgICAgIGYi'
        'LSB7Y2lkfSAoe2tpbmR9KTogb2N1cCB7YXZnOi4wZn0lIMK3IGZpbGEge2ZpbGF9IMK3IGVzcGVy'
        'YSB7d2FpdDouMWZ9bWluIMK3IHN0YXR1cyB7c3RhdHVzX3dvcmR9IgogICAgICAgICkKCiAgICBp'
        'ZiByb3V0ZSBpcyBub3QgTm9uZToKICAgICAgICBsaW5lcy5hcHBlbmQoIiIpCiAgICAgICAgbGlu'
        'ZXMuYXBwZW5kKCIjIyBST1VUSU5HIFJFQ09NRU5EQURPIEFHT1JBIikKICAgICAgICBsaW5lcy5h'
        'cHBlbmQoCiAgICAgICAgICAgIGYiLSBXQyBzdWdlcmlkbzoge3JvdXRlLnJlY29tbWVuZGVkX3Nl'
        'Y3Rpb259ICAiCiAgICAgICAgICAgIGYiwrcgY2FtaW5oYWRhIHtyb3V0ZS53YWxrX21pbjouMWZ9'
        'bWluICAiCiAgICAgICAgICAgIGYiwrcgZmlsYSB7cm91dGUucXVldWVfbWluOi4xZn1taW4gICIK'
        'ICAgICAgICAgICAgZiLCtyBjdXN0byB0b3RhbCB7cm91dGUudG90YWxfY29zdF9taW46LjFmfW1p'
        'biIKICAgICAgICApCiAgICAgICAgaWYgZ2V0YXR0cihyb3V0ZSwgImFsdGVybmF0aXZlcyIsIE5v'
        'bmUpOgogICAgICAgICAgICBhbHRzID0gIiwgIi5qb2luKHJvdXRlLmFsdGVybmF0aXZlc1s6M10p'
        'CiAgICAgICAgICAgIGxpbmVzLmFwcGVuZChmIi0gQWx0ZXJuYXRpdmFzOiB7YWx0c30iKQoKICAg'
        'IHJldHVybiAiXG4iLmpvaW4obGluZXMpCgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgU3lzdGVt'
        'IHByb21wdCDigJQgUFQtUFQsIGZhY3R1YWwsIHNlbSBpbnZlbnRhcgojIC0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0KX1NZU1RFTV9QUk9NUFQgPSAiIiLDiXMgbyBhc3Npc3RlbnRlIFBsYW50YU9TLCBsaWdh'
        'ZG8gZW0gdGVtcG8gcmVhbCBhb3MgOCBjbHVzdGVycyBXQyBkbyBSb2NrIGluIFJpbyBMaXNib2Eg'
        'MjAyNiAoUGFycXVlIFRlam8pLiBGYWxhcyBFWENMVVNJVkFNRU5URSBlbSBwb3J0dWd1w6pzIGV1'
        'cm9wZXUgKFBULVBULCBuw6NvIGJyYXNpbGVpcm8pLgoKUkVHUkFTIEVTVFJJVEFTOgotIFJlc3Bv'
        'bmRlIHNlbXByZSBjb20gYmFzZSBubyBibG9jbyAiRVNUQURPIExJVkUiIHF1ZSByZWNlYmVzIG5h'
        'IHBlcmd1bnRhLiBFc3NlIGJsb2NvIMOpIGEgw7puaWNhIGZvbnRlIGRlIHZlcmRhZGUuCi0gU2Ug'
        'YSBpbmZvcm1hw6fDo28gbsOjbyBlc3RpdmVyIG5vIGJsb2NvLCBkaXogY2xhcmFtZW50ZTogIlNl'
        'bSBkYWRvcyBkaXNwb27DrXZlaXMgc29icmUgaXNzbyBuZXN0ZSBtb21lbnRvLiIgTlVOQ0EgaW52'
        'ZW50ZXMgdmFsb3Jlcy4KLSBTw6ogY29uY2lzbzogMi00IGZyYXNlcy4gU2VtIGxpc3RhcyBsb25n'
        'YXMgYSBtZW5vcyBxdWUgcGXDp2FtLgotIFVzYSBuw7ptZXJvcyByZWFpcyBkbyBibG9jbyAob2N1'
        'cGHDp8OjbyAlLCBmaWxhcywgZXNwZXJhcykuIFJlZmVyZSBjbHVzdGVycyBjb21vIFdDLTAxLCBX'
        'Qy0wMiwgZXRjLgotIFF1YW5kbyByZWNvbWVuZGFyZXMgdW0gV0MsIGp1c3RpZmljYSBjb20gMS0y'
        'IG3DqXRyaWNhcyAoZXg6ICJXQy0wMyBlc3TDoSBjb20gMjglIGUgbWVpbyBtaW51dG8gZGUgZXNw'
        'ZXJhIikuCi0gV0MtMDUgZSBXQy0wNiBzw6NvIHVuaXNleC4gV0MtMDEvMDIvMDMvMDQvMDcvMDgg'
        'dMOqbSBzZWPDp8O1ZXMgbWFzY3VsaW5vIChNKSBlIGZlbWluaW5vIChGKSBzZXBhcmFkYXMuCi0g'
        'TnVuY2EgY2l0ZXM6ICJGPVAvRCIsICJGcmVlZG9tIEluZGV4IiwgIkRpc3RvcnRpb24iLCAic2Vl'
        'ZCIsICJoaXDDs3Rlc2UiLCAiRGV1Y2FsaW9uIiwgIkZSRUUgYWxnb3JpdGhtIi4gRm9jYS10ZSBu'
        'byBwcm9kdXRvOiBjb250YXIgcGVzc29hcywgcmVjb21lbmRhciBXQywgYWxlcnRhciBzb2JyZSBm'
        'aWxhcy4KLSBUb206IGRpcmVjdG8sIHByb2Zpc3Npb25hbCwgY2FsbW8uIE7Do28gw6lzIHZlbmRl'
        'ZG9yLgoiIiIKCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBHZW1pbmkgY2FsbAojIC0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0KZGVmIF9hbnN3ZXJfdmlhX2dlbWluaSgKICAgIG1lc3NhZ2U6IHN0ciwKICAg'
        'IGxpdmVfcGF5bG9hZDogT3B0aW9uYWxbTGl2ZVBheWxvYWRdLAogICAgcm91dGU6IE9wdGlvbmFs'
        'W0JhdGhyb29tUm91dGVEZWNpc2lvbl0sCiAgICB0czogZmxvYXQsCikgLT4gQ2hhdFJlc3BvbnNl'
        'OgogICAgIiIiQ2hhbWEgR2VtaW5pIDIuNSBGbGFzaCBjb20gY29udGV4dG8gKyBzeXN0ZW0gcHJv'
        'bXB0LiBQb2RlIGxldmFudGFyLiIiIgogICAgYXNzZXJ0IF9HRU1JTklfQ0xJRU5UIGlzIG5vdCBO'
        'b25lICAjIGdhcmFudGlkbyBwZWxvIGdhdGluZwogICAgZ2VuYWkgPSBfR0VNSU5JX0NMSUVOVAoK'
        'ICAgIGNvbnRleHRfYmxvY2sgPSBfYnVpbGRfY29udGV4dF9ibG9jayhsaXZlX3BheWxvYWQsIHJv'
        'dXRlKQoKICAgICMgVXNlciBwcm9tcHQgPSBjb250ZXh0byArIHBlcmd1bnRhIGRvIHV0aWxpemFk'
        'b3IKICAgIHVzZXJfcHJvbXB0ID0gKAogICAgICAgIGYie2NvbnRleHRfYmxvY2t9XG5cbiIKICAg'
        'ICAgICBmIiMjIFBFUkdVTlRBIERPIFVUSUxJWkFET1JcbiIKICAgICAgICBmInttZXNzYWdlLnN0'
        'cmlwKCl9IgogICAgKQoKICAgICMgU0RLIGdlbmFpID49IDAuNTogR2VuZXJhdGl2ZU1vZGVsICsg'
        'c3lzdGVtX2luc3RydWN0aW9uCiAgICBtb2RlbCA9IGdlbmFpLkdlbmVyYXRpdmVNb2RlbCgKICAg'
        'ICAgICBtb2RlbF9uYW1lPUdFTUlOSV9NT0RFTCwKICAgICAgICBzeXN0ZW1faW5zdHJ1Y3Rpb249'
        'X1NZU1RFTV9QUk9NUFQsCiAgICAgICAgZ2VuZXJhdGlvbl9jb25maWc9ewogICAgICAgICAgICAi'
        'dGVtcGVyYXR1cmUiOiBHRU1JTklfVEVNUEVSQVRVUkUsCiAgICAgICAgICAgICJtYXhfb3V0cHV0'
        'X3Rva2VucyI6IEdFTUlOSV9NQVhfVE9LRU5TLAogICAgICAgICAgICAidG9wX3AiOiAwLjk1LAog'
        'ICAgICAgIH0sCiAgICApCgogICAgIyBUaW1lb3V0IHZpYSByZXF1ZXN0X29wdGlvbnMgKHN1cG9y'
        'dGFkbyBwZWxvIFNESykKICAgIHJlc3BvbnNlID0gbW9kZWwuZ2VuZXJhdGVfY29udGVudCgKICAg'
        'ICAgICB1c2VyX3Byb21wdCwKICAgICAgICByZXF1ZXN0X29wdGlvbnM9eyJ0aW1lb3V0IjogR0VN'
        'SU5JX1RJTUVPVVRfU30sCiAgICApCgogICAgcmVwbHlfdGV4dDogc3RyID0gIiIKICAgIHRyeToK'
        'ICAgICAgICByZXBseV90ZXh0ID0gKHJlc3BvbnNlLnRleHQgb3IgIiIpLnN0cmlwKCkKICAgIGV4'
        'Y2VwdCBFeGNlcHRpb246CiAgICAgICAgIyBSZXNwb3N0YSBibG9xdWVhZGEgcG9yIHNhZmV0eSBm'
        'aWx0ZXIgb3UgZXN0cnV0dXJhIGluZXNwZXJhZGEKICAgICAgICBjYW5kaWRhdGVzID0gZ2V0YXR0'
        'cihyZXNwb25zZSwgImNhbmRpZGF0ZXMiLCBOb25lKSBvciBbXQogICAgICAgIGlmIGNhbmRpZGF0'
        'ZXM6CiAgICAgICAgICAgIHBhcnRzID0gZ2V0YXR0cihjYW5kaWRhdGVzWzBdLmNvbnRlbnQsICJw'
        'YXJ0cyIsIE5vbmUpIG9yIFtdCiAgICAgICAgICAgIHJlcGx5X3RleHQgPSAiIi5qb2luKGdldGF0'
        'dHIocCwgInRleHQiLCAiIikgZm9yIHAgaW4gcGFydHMpLnN0cmlwKCkKCiAgICBpZiBub3QgcmVw'
        'bHlfdGV4dDoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoIkdlbWluaSBkZXZvbHZldSByZXNw'
        'b3N0YSB2YXppYSIpCgogICAgcmV0dXJuIENoYXRSZXNwb25zZSgKICAgICAgICByZXBseT1yZXBs'
        'eV90ZXh0LAogICAgICAgIGdyb3VuZGVkPVRydWUsCiAgICAgICAgbGl2ZV9kYXRhX2F2YWlsYWJs'
        'ZT1saXZlX3BheWxvYWQgaXMgbm90IE5vbmUsCiAgICAgICAgdHM9dHMsCiAgICApCgoKIyAtLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tCiMgRmFsbGJhY2sgcmVncmEtYmFzZWQgZW0gUFQtUFQgKG7Do28gZW0g'
        'aW5nbMOqcykKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCmRlZiBfYW5zd2VyX3ZpYV9ydWxlc19wdCgK'
        'ICAgIG1lc3NhZ2U6IHN0ciwKICAgIGxpdmVfcGF5bG9hZDogT3B0aW9uYWxbTGl2ZVBheWxvYWRd'
        'LAogICAgcm91dGU6IE9wdGlvbmFsW0JhdGhyb29tUm91dGVEZWNpc2lvbl0sCiAgICB0czogZmxv'
        'YXQsCikgLT4gQ2hhdFJlc3BvbnNlOgogICAgbXNnID0gKG1lc3NhZ2Ugb3IgIiIpLnN0cmlwKCkK'
        'ICAgIGlmIGxpdmVfcGF5bG9hZCBpcyBOb25lOgogICAgICAgIHJldHVybiBDaGF0UmVzcG9uc2Uo'
        'CiAgICAgICAgICAgIHJlcGx5PSJTZW0gZGFkb3MgbGl2ZSBkaXNwb27DrXZlaXMgbmVzdGUgbW9t'
        'ZW50by4gVGVudGEgZGUgbm92byBlbSBhbGd1bnMgc2VndW5kb3MuIiwKICAgICAgICAgICAgZ3Jv'
        'dW5kZWQ9RmFsc2UsCiAgICAgICAgICAgIGxpdmVfZGF0YV9hdmFpbGFibGU9RmFsc2UsCiAgICAg'
        'ICAgICAgIHRzPXRzLAogICAgICAgICkKCiAgICBrcGlzID0gbGl2ZV9wYXlsb2FkLmtwaXMKICAg'
        'IHNlY3Rpb25zID0gbGlzdChsaXZlX3BheWxvYWQuc2VjdGlvbnMpCiAgICBpZiBub3Qgc2VjdGlv'
        'bnM6CiAgICAgICAgcmV0dXJuIENoYXRSZXNwb25zZSgKICAgICAgICAgICAgcmVwbHk9Ik5lbmh1'
        'bWEgc2Vjw6fDo28gYSByZXBvcnRhciBkYWRvcyBhZ29yYS4iLAogICAgICAgICAgICBncm91bmRl'
        'ZD1UcnVlLAogICAgICAgICAgICBsaXZlX2RhdGFfYXZhaWxhYmxlPVRydWUsCiAgICAgICAgICAg'
        'IHRzPXRzLAogICAgICAgICkKCiAgICAjIFJPVVRJTkcgLyBxdWFsIFdDIGlyCiAgICBpZiBfY29u'
        'dGFpbnNfYW55KG1zZywgX0tFWVdPUkRTX1dISUNIKSBvciBfY29udGFpbnNfYW55KG1zZywgX0tF'
        'WVdPUkRTX0ZBU1RFU1QpOgogICAgICAgIGlmIHJvdXRlIGlzIG5vdCBOb25lOgogICAgICAgICAg'
        'ICByZXBseSA9ICgKICAgICAgICAgICAgICAgIGYiUmVjb21lbmRvIHtyb3V0ZS5yZWNvbW1lbmRl'
        'ZF9zZWN0aW9ufTogY2FtaW5oYWRhIGRlIHtyb3V0ZS53YWxrX21pbjouMWZ9IG1pbiAiCiAgICAg'
        'ICAgICAgICAgICBmImUgZmlsYSBkZSB7cm91dGUucXVldWVfbWluOi4xZn0gbWluIOKAlCBjdXN0'
        'byB0b3RhbCB7cm91dGUudG90YWxfY29zdF9taW46LjFmfSBtaW4uIgogICAgICAgICAgICApCiAg'
        'ICAgICAgICAgIGlmIGdldGF0dHIocm91dGUsICJhbHRlcm5hdGl2ZXMiLCBOb25lKToKICAgICAg'
        'ICAgICAgICAgIGFsdHMgPSAiLCAiLmpvaW4ocm91dGUuYWx0ZXJuYXRpdmVzWzoyXSkKICAgICAg'
        'ICAgICAgICAgIHJlcGx5ICs9IGYiIEFsdGVybmF0aXZhczoge2FsdHN9LiIKICAgICAgICBlbHNl'
        'OgogICAgICAgICAgICBiZXN0ID0gbWluKHNlY3Rpb25zLCBrZXk9bGFtYmRhIHM6IHMub2N1cGFj'
        'YW9fcGN0ICsgcy50ZW1wb19lc3BlcmFfbWluICogNSkKICAgICAgICAgICAgcmVwbHkgPSAoCiAg'
        'ICAgICAgICAgICAgICBmIk8gbWFpcyByw6FwaWRvIGFnb3JhIMOpIHtiZXN0LnNlY3Rpb25faWR9'
        'OiB7YmVzdC5vY3VwYWNhb19wY3Q6LjBmfSUgZGUgb2N1cGHDp8OjbywgIgogICAgICAgICAgICAg'
        'ICAgZiJlc3BlcmEgZGUge2Jlc3QudGVtcG9fZXNwZXJhX21pbjouMWZ9IG1pbi4iCiAgICAgICAg'
        'ICAgICkKICAgICAgICByZXR1cm4gQ2hhdFJlc3BvbnNlKHJlcGx5PXJlcGx5LCBncm91bmRlZD1U'
        'cnVlLCBsaXZlX2RhdGFfYXZhaWxhYmxlPVRydWUsIHRzPXRzKQoKICAgICMgQ0hFSU8gLyBFVklU'
        'QVIKICAgIGlmIF9jb250YWluc19hbnkobXNnLCBfS0VZV09SRFNfRlVMTCkgb3IgX2NvbnRhaW5z'
        'X2FueShtc2csIF9LRVlXT1JEU19BVk9JRCk6CiAgICAgICAgd29yc3QgPSBtYXgoc2VjdGlvbnMs'
        'IGtleT1sYW1iZGEgczogcy5vY3VwYWNhb19wY3QpCiAgICAgICAgcmVwbHkgPSAoCiAgICAgICAg'
        'ICAgIGYiTWFpcyBjaGVpbyBhZ29yYToge3dvcnN0LnNlY3Rpb25faWR9IGNvbSB7d29yc3Qub2N1'
        'cGFjYW9fcGN0Oi4wZn0lIGRlIG9jdXBhw6fDo28gIgogICAgICAgICAgICBmImUgZmlsYSBkZSB7'
        'd29yc3QuZmlsYV9hdHVhbH0gcGVzc29hcyAoZXNwZXJhIHt3b3JzdC50ZW1wb19lc3BlcmFfbWlu'
        'Oi4xZn0gbWluKS4gIgogICAgICAgICAgICAiQ29uc2lkZXJhIG91dHJvIGNsdXN0ZXIuIgogICAg'
        'ICAgICkKICAgICAgICByZXR1cm4gQ2hhdFJlc3BvbnNlKHJlcGx5PXJlcGx5LCBncm91bmRlZD1U'
        'cnVlLCBsaXZlX2RhdGFfYXZhaWxhYmxlPVRydWUsIHRzPXRzKQoKICAgICMgU0VOU09SRVMKICAg'
        'IGlmIF9jb250YWluc19hbnkobXNnLCBfS0VZV09SRFNfU0VOU09SKToKICAgICAgICBzaW1fZmxh'
        'ZyA9ICJzaW11bGFkb3MiIGlmIGtwaXMuYW55X3NpbXVsYXRlZCBlbHNlICJsaXZlIgogICAgICAg'
        'IHJlcGx5ID0gKAogICAgICAgICAgICBmIk9zIGRhZG9zIGVzdMOjbyB7c2ltX2ZsYWd9LiBPIHNp'
        'c3RlbWEgY29tYmluYSBjb250YWRvcmVzIElSIGRlIGVudHJhZGEgZSBzYcOtZGEgKHBlc28gNTAl'
        'KSwgIgogICAgICAgICAgICAiYWdyZWdhw6fDo28gV2lGaSAoMzAlKSBlIHZhbGlkYcOnw6NvIHBv'
        'ciBjw6JtYXJhICgyMCUpLiIKICAgICAgICApCiAgICAgICAgcmV0dXJuIENoYXRSZXNwb25zZShy'
        'ZXBseT1yZXBseSwgZ3JvdW5kZWQ9VHJ1ZSwgbGl2ZV9kYXRhX2F2YWlsYWJsZT1UcnVlLCB0cz10'
        'cykKCiAgICAjIFNIT1dTCiAgICBpZiBfY29udGFpbnNfYW55KG1zZywgX0tFWVdPUkRTX1NIT1cp'
        'OgogICAgICAgIHJlcGx5ID0gKAogICAgICAgICAgICAiUm9jayBpbiBSaW8gTGlzYm9hIDIwMjYg'
        'ZGVjb3JyZSBub3MgZGlhcyAyMOKAkzIxIGUgMjfigJMyOCBkZSBKdW5oby4gIgogICAgICAgICAg'
        'ICAiRHVyYW50ZSBvcyBoZWFkbGluZXJzIG8gcGljbyBkZSB1dGlsaXphw6fDo28gZG9zIFdDIMOp'
        'IHNpZ25pZmljYXRpdm8g4oCUICIKICAgICAgICAgICAgImNvbnN1bHRhIC92Mi9zaG93cyBwYXJh'
        'IG8gc3VyZ2UgZXNwZXJhZG8gcG9yIHNob3cuIgogICAgICAgICkKICAgICAgICByZXR1cm4gQ2hh'
        'dFJlc3BvbnNlKHJlcGx5PXJlcGx5LCBncm91bmRlZD1UcnVlLCBsaXZlX2RhdGFfYXZhaWxhYmxl'
        'PVRydWUsIHRzPXRzKQoKICAgICMgT1BTCiAgICBpZiBfY29udGFpbnNfYW55KG1zZywgX0tFWVdP'
        'UkRTX09QUyk6CiAgICAgICAgdG90YWwgPSBsZW4oc2VjdGlvbnMpCiAgICAgICAgb25saW5lID0g'
        'c3VtKDEgZm9yIHMgaW4gc2VjdGlvbnMgaWYgcy5zdGF0dXMgIT0gIm9mZmxpbmUiKQogICAgICAg'
        'IHJlcGx5ID0gKAogICAgICAgICAgICBmIk9wZXJhw6fDtWVzOiB7b25saW5lfSBkZSB7dG90YWx9'
        'IHNlY8Onw7VlcyBvbmxpbmUgwrcge2twaXMuY3JpdGljYWxfc2VjdGlvbnN9IGNyw610aWNhcyDC'
        'tyAiCiAgICAgICAgICAgIGYib2N1cGHDp8OjbyBtw6lkaWEge2twaXMuYXZnX29jdXBhY2FvX3Bj'
        'dDouMGZ9JSDCtyBmaWxhIHRvdGFsIHtrcGlzLnRvdGFsX2ZpbGF9IHBlc3NvYXMuIgogICAgICAg'
        'ICkKICAgICAgICByZXR1cm4gQ2hhdFJlc3BvbnNlKHJlcGx5PXJlcGx5LCBncm91bmRlZD1UcnVl'
        'LCBsaXZlX2RhdGFfYXZhaWxhYmxlPVRydWUsIHRzPXRzKQoKICAgICMgRGVmYXVsdAogICAgcmVw'
        'bHkgPSAoCiAgICAgICAgZiJFc3RhZG8gYWN0dWFsOiB7a3Bpcy5hdmdfb2N1cGFjYW9fcGN0Oi4w'
        'Zn0lIGRlIG9jdXBhw6fDo28gbcOpZGlhIGVtIHtsZW4oc2VjdGlvbnMpfSBzZWPDp8O1ZXMgV0Ms'
        'ICIKICAgICAgICBmImZpbGEgdG90YWwgZGUge2twaXMudG90YWxfZmlsYX0gcGVzc29hcywge2tw'
        'aXMuY3JpdGljYWxfc2VjdGlvbnN9IHNlY8Onw7VlcyBjcsOtdGljYXMuICIKICAgICAgICAiUGVy'
        'Z3VudGEtbWUgJ3F1YWwgbyBXQyBtYWlzIHLDoXBpZG8/JywgJ29uZGUgZXN0w6EgbWFpcyBjaGVp'
        'bz8nIG91ICdlc3RhZG8gZG9zIHNlbnNvcmVzJy4iCiAgICApCiAgICByZXR1cm4gQ2hhdFJlc3Bv'
        'bnNlKHJlcGx5PXJlcGx5LCBncm91bmRlZD1UcnVlLCBsaXZlX2RhdGFfYXZhaWxhYmxlPVRydWUs'
        'IHRzPXRzKQoKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEVudHJ5cG9pbnQgcMO6YmxpY28gKGFz'
        'c2luYXR1cmEgcHJlc2VydmFkYSkKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t'
        'LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCmRlZiBhbnN3ZXJfY2hh'
        'dCgKICAgIG1lc3NhZ2U6IHN0ciwKICAgIGxpdmVfcGF5bG9hZDogT3B0aW9uYWxbTGl2ZVBheWxv'
        'YWRdLAogICAgcm91dGU6IE9wdGlvbmFsW0JhdGhyb29tUm91dGVEZWNpc2lvbl0gPSBOb25lLAop'
        'IC0+IENoYXRSZXNwb25zZToKICAgICIiIlJlc3BvbmRlIGEgdW1hIG1lbnNhZ2VtIGRvIHV0aWxp'
        'emFkb3IuIFRlbnRhIEdlbWluaSBwcmltZWlybywgZGVwb2lzIGNhaSBlbSByZWdyYXMgUFQtUFQu'
        'IiIiCiAgICB0cyA9IHRpbWUudGltZSgpCiAgICBzYWZlX21zZyA9IChtZXNzYWdlIG9yICIiKS5z'
        'dHJpcCgpCiAgICBpZiBub3Qgc2FmZV9tc2c6CiAgICAgICAgcmV0dXJuIENoYXRSZXNwb25zZSgK'
        'ICAgICAgICAgICAgcmVwbHk9IkZhei1tZSB1bWEgcGVyZ3VudGEgc29icmUgb3MgY2x1c3RlcnMg'
        'V0MsIGZpbGFzLCBvdSBzaG93cy4iLAogICAgICAgICAgICBncm91bmRlZD1GYWxzZSwKICAgICAg'
        'ICAgICAgbGl2ZV9kYXRhX2F2YWlsYWJsZT1saXZlX3BheWxvYWQgaXMgbm90IE5vbmUsCiAgICAg'
        'ICAgICAgIHRzPXRzLAogICAgICAgICkKCiAgICAjIDEpIFRlbnRhIEdlbWluaQogICAgaWYgX0dF'
        'TUlOSV9BVkFJTEFCTEU6CiAgICAgICAgdHJ5OgogICAgICAgICAgICByZXR1cm4gX2Fuc3dlcl92'
        'aWFfZ2VtaW5pKHNhZmVfbXNnLCBsaXZlX3BheWxvYWQsIHJvdXRlLCB0cykKICAgICAgICBleGNl'
        'cHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgIGxvZy53YXJuaW5nKGYiR2VtaW5pIGZhbGhv'
        'dSAoe2UuX19jbGFzc19fLl9fbmFtZV9ffToge2V9KSDigJQgZmFsbGJhY2sgUFQtUFQiKQoKICAg'
        'ICMgMikgRmFsbGJhY2sgcmVncmEtYmFzZWQgUFQtUFQKICAgIHJldHVybiBfYW5zd2VyX3ZpYV9y'
        'dWxlc19wdChzYWZlX21zZywgbGl2ZV9wYXlsb2FkLCByb3V0ZSwgdHMpCg=='
    ),
}

REQUIREMENT_LINE = "google-generativeai>=0.8.0"

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
        print("ERRO: corre a partir de ~/planta_rock4 (precisa de app/ e requirements.txt)")
        sys.exit(1)

    # 1. Backup do chat.py antigo
    section("1. Backup do chat.py antigo")
    old = root / "app" / "services" / "chat.py"
    if old.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = old.with_suffix(f".py.bak.{stamp}")
        shutil.copy2(old, backup)
        print(f"  backup → {backup.name}")

    # 2. Escrever chat.py novo
    section("2. Escrever app/services/chat.py com Gemini")
    for rel, chunks in FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode("".join(chunks))
        target.write_bytes(data)
        print(f"  OK  {rel}  ({len(data)} B)")

    # 3. Adicionar google-generativeai ao requirements.txt
    section("3. Actualizar requirements.txt")
    req = root / "requirements.txt"
    current = req.read_text()
    if "google-generativeai" in current:
        print("  google-generativeai já presente — skip")
    else:
        new_content = current.rstrip() + "\n" + REQUIREMENT_LINE + "\n"
        req.write_text(new_content)
        print(f"  adicionado: {REQUIREMENT_LINE}")

    # 4. Validar sintaxe Python
    section("4. Validar sintaxe Python")
    ok = run("python3 -m py_compile app/services/chat.py", cwd=str(root))
    if not ok:
        print("ERRO: sintaxe inválida — não vou fazer push")
        sys.exit(1)
    print("  ✓ chat.py compila limpo")

    # 5. Commit + push
    section("5. Commit + push")
    run("git add app/services/chat.py requirements.txt", cwd=str(root))
    run("git status --short", cwd=str(root))
    msg = "feat(chat): gemini 2.5 flash + fallback regra-based PT-PT"
    run(f'git commit -m "{msg}"', cwd=str(root))
    run("git push", cwd=str(root))

    # 6. Confirmar Railway vars
    section("6. Lembrete · Railway env vars")
    print("   As vars GEMINI_API_KEY e GEMINI_MODEL já estão no Railway.")
    print("   O push vai disparar rebuild automático (90-120 s).")
    print("")
    print("   Aguarda 2 min e testa:")
    print("")
    print("   curl -s -X POST https://api.plantarockinrio.com/api/v1/chat \\")
    print("     -H content-type:application/json \\")
    print("     -d '{\"message\":\"Resume em duas frases o estado dos clusters\"}' \\")
    print("     | python3 -m json.tool")
    print("")
    print("   Antes:  Current status: 32% average occupancy across 14 WC sections...")
    print("   Depois: A ocupação média ronda 32% nos 8 clusters, com WC-02 e WC-07")
    print("           a aproximarem-se dos 40%. Nenhum cluster em estado crítico agora.")
    print("")
    print("   Se ainda devolver inglês após 2 min, vê os logs:")
    print("   railway logs --service planta_rock4 | grep -i gemini")

if __name__ == "__main__":
    main()

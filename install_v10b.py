#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v10b — HOTFIX

Corrige 3 problemas reportados pelo CEO:
  1. Terminal preto no fundo (footer LiveTerminal)
     → REMOVIDO do layout.tsx do /v2
  2. Chatbot pequeno do canto
     → SUBSTITUIDO por PlantaSearchBar (estilo Claude/ChatGPT)
     → input grande ancorado ao fundo, 🎤 + 📎 + "Ask Planta..." + "PlantaOS can make mistakes"
  3. TopBar antigo restaurado (preservar design original)
     → restaura TopBar.tsx do backup .bak.v10.*
     → adiciona links: Limpeza, SCOR, Pipelines
"""

import base64, os, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),])

SEARCHBAR_B64 = (
    'J3VzZSBjbGllbnQnOwoKaW1wb3J0IHsgdXNlRWZmZWN0LCB1c2VSZWYsIHVzZVN0YXRlIH0gZnJv'
    'bSAncmVhY3QnOwoKY29uc3QgQVBJX0JBU0UgPSBwcm9jZXNzLmVudi5ORVhUX1BVQkxJQ19BUElf'
    'QkFTRSB8fCAnaHR0cHM6Ly9hcGkucGxhbnRhcm9ja2lucmlvLmNvbSc7CgppbnRlcmZhY2UgTXNn'
    'IHsKICByb2xlOiAndXNlcicgfCAnYXNzaXN0YW50JzsKICBjb250ZW50OiBzdHJpbmc7CiAgdHM6'
    'IG51bWJlcjsKfQoKZXhwb3J0IGRlZmF1bHQgZnVuY3Rpb24gUGxhbnRhU2VhcmNoQmFyKCkgewog'
    'IGNvbnN0IFtvcGVuLCBzZXRPcGVuXSA9IHVzZVN0YXRlKGZhbHNlKTsKICBjb25zdCBbaW5wdXQs'
    'IHNldElucHV0XSA9IHVzZVN0YXRlKCcnKTsKICBjb25zdCBbbWVzc2FnZXMsIHNldE1lc3NhZ2Vz'
    'XSA9IHVzZVN0YXRlPE1zZ1tdPihbXSk7CiAgY29uc3QgW3NlbmRpbmcsIHNldFNlbmRpbmddID0g'
    'dXNlU3RhdGUoZmFsc2UpOwogIGNvbnN0IG1lc3NhZ2VzRW5kUmVmID0gdXNlUmVmPEhUTUxEaXZF'
    'bGVtZW50PihudWxsKTsKICBjb25zdCBpbnB1dFJlZiA9IHVzZVJlZjxIVE1MSW5wdXRFbGVtZW50'
    'PihudWxsKTsKCiAgLy8gQXV0by1zY3JvbGwgbWVzc2FnZXMKICB1c2VFZmZlY3QoKCkgPT4gewog'
    'ICAgaWYgKG1lc3NhZ2VzRW5kUmVmLmN1cnJlbnQpIHsKICAgICAgbWVzc2FnZXNFbmRSZWYuY3Vy'
    'cmVudC5zY3JvbGxJbnRvVmlldyh7IGJlaGF2aW9yOiAnc21vb3RoJyB9KTsKICAgIH0KICB9LCBb'
    'bWVzc2FnZXNdKTsKCiAgLy8gRm9jdXMgaW5wdXQgd2hlbiBvcGVuCiAgdXNlRWZmZWN0KCgpID0+'
    'IHsKICAgIGlmIChvcGVuICYmIGlucHV0UmVmLmN1cnJlbnQpIHsKICAgICAgc2V0VGltZW91dCgo'
    'KSA9PiBpbnB1dFJlZi5jdXJyZW50Py5mb2N1cygpLCA1MCk7CiAgICB9CiAgfSwgW29wZW5dKTsK'
    'CiAgY29uc3Qgc2VuZCA9IGFzeW5jICh0ZXh0Pzogc3RyaW5nKSA9PiB7CiAgICBjb25zdCBjb250'
    'ZW50ID0gKHRleHQgPz8gaW5wdXQpLnRyaW0oKTsKICAgIGlmICghY29udGVudCB8fCBzZW5kaW5n'
    'KSByZXR1cm47CgogICAgLy8gQWJyaXIgcGFpbmVsIGFvIGVudmlhciBwcmltZWlyYSBtZW5zYWdl'
    'bQogICAgaWYgKCFvcGVuKSBzZXRPcGVuKHRydWUpOwoKICAgIHNldE1lc3NhZ2VzKG0gPT4gWy4u'
    'Lm0sIHsgcm9sZTogJ3VzZXInLCBjb250ZW50LCB0czogRGF0ZS5ub3coKSB9XSk7CiAgICBzZXRJ'
    'bnB1dCgnJyk7CiAgICBzZXRTZW5kaW5nKHRydWUpOwoKICAgIHRyeSB7CiAgICAgIGNvbnN0IHIg'
    'PSBhd2FpdCBmZXRjaChgJHtBUElfQkFTRX0vYXBpL3YxL2NoYXQvYXNrYCwgewogICAgICAgIG1l'
    'dGhvZDogJ1BPU1QnLAogICAgICAgIGhlYWRlcnM6IHsgJ2NvbnRlbnQtdHlwZSc6ICdhcHBsaWNh'
    'dGlvbi9qc29uJyB9LAogICAgICAgIGJvZHk6IEpTT04uc3RyaW5naWZ5KHsgbWVzc2FnZTogY29u'
    'dGVudCB9KSwKICAgICAgfSk7CiAgICAgIGxldCByZXBseSA9ICdEZXNjdWxwYSwgbsOjbyBjb25z'
    'ZWd1aSBwcm9jZXNzYXIuJzsKICAgICAgaWYgKHIub2spIHsKICAgICAgICBjb25zdCBqID0gYXdh'
    'aXQgci5qc29uKCk7CiAgICAgICAgcmVwbHkgPSBqLnJlcGx5IHx8IGoubWVzc2FnZSB8fCBqLnJl'
    'c3BvbnNlIHx8IEpTT04uc3RyaW5naWZ5KGopLnNsaWNlKDAsIDIwMCk7CiAgICAgIH0gZWxzZSB7'
    'CiAgICAgICAgcmVwbHkgPSBgRXJybyBkbyBzZXJ2aWRvciAoJHtyLnN0YXR1c30pLiBUZW50YSBu'
    'b3ZhbWVudGUuYDsKICAgICAgfQogICAgICBzZXRNZXNzYWdlcyhtID0+IFsuLi5tLCB7IHJvbGU6'
    'ICdhc3Npc3RhbnQnLCBjb250ZW50OiByZXBseSwgdHM6IERhdGUubm93KCkgfV0pOwogICAgfSBj'
    'YXRjaCAoZSkgewogICAgICBzZXRNZXNzYWdlcyhtID0+IFsuLi5tLCB7CiAgICAgICAgcm9sZTog'
    'J2Fzc2lzdGFudCcsCiAgICAgICAgY29udGVudDogJ1Byb2JsZW1hIGRlIGxpZ2HDp8Ojby4gVmVy'
    'aWZpY2EgYSB0dWEgcmVkZS4nLAogICAgICAgIHRzOiBEYXRlLm5vdygpLAogICAgICB9XSk7CiAg'
    'ICB9IGZpbmFsbHkgewogICAgICBzZXRTZW5kaW5nKGZhbHNlKTsKICAgIH0KICB9OwoKICByZXR1'
    'cm4gKAogICAgPD4KICAgICAgey8qIFBhaW5lbCBkZSBtZW5zYWdlbnMgKGFjaW1hIGRhIHNlYXJj'
    'aGJhciBxdWFuZG8gYWJlcnRvKSAqL30KICAgICAge29wZW4gJiYgbWVzc2FnZXMubGVuZ3RoID4g'
    'MCAmJiAoCiAgICAgICAgPGRpdgogICAgICAgICAgb25DbGljaz17KGUpID0+IHsKICAgICAgICAg'
    'ICAgLy8gQ2xpY2sgbm8gYmFja2Ryb3AgZmVjaGEKICAgICAgICAgICAgaWYgKGUudGFyZ2V0ID09'
    'PSBlLmN1cnJlbnRUYXJnZXQpIHNldE9wZW4oZmFsc2UpOwogICAgICAgICAgfX0KICAgICAgICAg'
    'IHN0eWxlPXt7CiAgICAgICAgICAgIHBvc2l0aW9uOiAnZml4ZWQnLAogICAgICAgICAgICBpbnNl'
    'dDogMCwKICAgICAgICAgICAgYmFja2dyb3VuZDogJ3JnYmEoMCwwLDAsMC4zKScsCiAgICAgICAg'
    'ICAgIGJhY2tkcm9wRmlsdGVyOiAnYmx1cig0cHgpJywKICAgICAgICAgICAgV2Via2l0QmFja2Ry'
    'b3BGaWx0ZXI6ICdibHVyKDRweCknLAogICAgICAgICAgICB6SW5kZXg6IDk5OCwKICAgICAgICAg'
    'ICAgZGlzcGxheTogJ2ZsZXgnLAogICAgICAgICAgICBmbGV4RGlyZWN0aW9uOiAnY29sdW1uJywK'
    'ICAgICAgICAgICAganVzdGlmeUNvbnRlbnQ6ICdmbGV4LWVuZCcsCiAgICAgICAgICAgIHBhZGRp'
    'bmdCb3R0b206IDExMCwKICAgICAgICAgICAgcG9pbnRlckV2ZW50czogJ2F1dG8nLAogICAgICAg'
    'ICAgfX0KICAgICAgICA+CiAgICAgICAgICA8ZGl2CiAgICAgICAgICAgIHN0eWxlPXt7CiAgICAg'
    'ICAgICAgICAgbWF4V2lkdGg6IDc2MCwKICAgICAgICAgICAgICB3aWR0aDogJ2NhbGMoMTAwJSAt'
    'IDMycHgpJywKICAgICAgICAgICAgICBtYXJnaW46ICcwIGF1dG8nLAogICAgICAgICAgICAgIG1h'
    'eEhlaWdodDogJ21pbig2MHZoLCA1MDBweCknLAogICAgICAgICAgICAgIG92ZXJmbG93WTogJ2F1'
    'dG8nLAogICAgICAgICAgICAgIHBhZGRpbmc6IDE2LAogICAgICAgICAgICAgIGRpc3BsYXk6ICdm'
    'bGV4JywKICAgICAgICAgICAgICBmbGV4RGlyZWN0aW9uOiAnY29sdW1uJywKICAgICAgICAgICAg'
    'ICBnYXA6IDEwLAogICAgICAgICAgICB9fQogICAgICAgICAgPgogICAgICAgICAgICB7bWVzc2Fn'
    'ZXMubWFwKChtLCBpKSA9PiAoCiAgICAgICAgICAgICAgPGRpdgogICAgICAgICAgICAgICAga2V5'
    'PXtpfQogICAgICAgICAgICAgICAgc3R5bGU9e3sKICAgICAgICAgICAgICAgICAgYWxpZ25TZWxm'
    'OiBtLnJvbGUgPT09ICd1c2VyJyA/ICdmbGV4LWVuZCcgOiAnZmxleC1zdGFydCcsCiAgICAgICAg'
    'ICAgICAgICAgIGJhY2tncm91bmQ6IG0ucm9sZSA9PT0gJ3VzZXInID8gJyMxQjNBMjEnIDogJ3do'
    'aXRlJywKICAgICAgICAgICAgICAgICAgY29sb3I6IG0ucm9sZSA9PT0gJ3VzZXInID8gJ3doaXRl'
    'JyA6ICcjMUExQTFBJywKICAgICAgICAgICAgICAgICAgcGFkZGluZzogJzEwcHggMTRweCcsCiAg'
    'ICAgICAgICAgICAgICAgIGJvcmRlclJhZGl1czogMTQsCiAgICAgICAgICAgICAgICAgIG1heFdp'
    'ZHRoOiAnODUlJywKICAgICAgICAgICAgICAgICAgZm9udFNpemU6IDE0LAogICAgICAgICAgICAg'
    'ICAgICBsaW5lSGVpZ2h0OiAxLjUsCiAgICAgICAgICAgICAgICAgIHdoaXRlU3BhY2U6ICdwcmUt'
    'd3JhcCcsCiAgICAgICAgICAgICAgICAgIGJveFNoYWRvdzogJzAgMnB4IDhweCByZ2JhKDAsMCww'
    'LDAuMDgpJywKICAgICAgICAgICAgICAgICAgYm9yZGVyOiBtLnJvbGUgPT09ICdhc3Npc3RhbnQn'
    'ID8gJzFweCBzb2xpZCByZ2JhKDAsMCwwLDAuMDYpJyA6ICdub25lJywKICAgICAgICAgICAgICAg'
    'IH19CiAgICAgICAgICAgICAgPnttLmNvbnRlbnR9PC9kaXY+CiAgICAgICAgICAgICkpfQogICAg'
    'ICAgICAgICB7c2VuZGluZyAmJiAoCiAgICAgICAgICAgICAgPGRpdiBzdHlsZT17ewogICAgICAg'
    'ICAgICAgICAgYWxpZ25TZWxmOiAnZmxleC1zdGFydCcsCiAgICAgICAgICAgICAgICBiYWNrZ3Jv'
    'dW5kOiAnd2hpdGUnLAogICAgICAgICAgICAgICAgcGFkZGluZzogJzEwcHggMTRweCcsCiAgICAg'
    'ICAgICAgICAgICBib3JkZXJSYWRpdXM6IDE0LAogICAgICAgICAgICAgICAgYm9yZGVyOiAnMXB4'
    'IHNvbGlkIHJnYmEoMCwwLDAsMC4wNiknLAogICAgICAgICAgICAgICAgZm9udFNpemU6IDEzLAog'
    'ICAgICAgICAgICAgICAgY29sb3I6ICcjODg4JywKICAgICAgICAgICAgICAgIGJveFNoYWRvdzog'
    'JzAgMnB4IDhweCByZ2JhKDAsMCwwLDAuMDgpJywKICAgICAgICAgICAgICB9fT4KICAgICAgICAg'
    'ICAgICAgIDxzcGFuIHN0eWxlPXt7IGFuaW1hdGlvbjogJ3BsYW50YS1ibGluayAxLjRzIGluZmlu'
    'aXRlJyB9fT7il48g4pePIOKXjzwvc3Bhbj4KICAgICAgICAgICAgICA8L2Rpdj4KICAgICAgICAg'
    'ICAgKX0KICAgICAgICAgICAgPGRpdiByZWY9e21lc3NhZ2VzRW5kUmVmfSAvPgogICAgICAgICAg'
    'PC9kaXY+CiAgICAgICAgPC9kaXY+CiAgICAgICl9CgogICAgICB7LyogU2VhcmNoQmFyIGZpeGEg'
    'bm8gZnVuZG8gKi99CiAgICAgIDxkaXYKICAgICAgICBzdHlsZT17ewogICAgICAgICAgcG9zaXRp'
    'b246ICdmaXhlZCcsCiAgICAgICAgICBib3R0b206IDI0LAogICAgICAgICAgbGVmdDogJzUwJScs'
    'CiAgICAgICAgICB0cmFuc2Zvcm06ICd0cmFuc2xhdGVYKC01MCUpJywKICAgICAgICAgIHdpZHRo'
    'OiAnbWluKDc2MHB4LCBjYWxjKDEwMCUgLSAzMnB4KSknLAogICAgICAgICAgekluZGV4OiA5OTks'
    'CiAgICAgICAgfX0KICAgICAgPgogICAgICAgIHsvKiBYIGNsb3NlIGJ1dHRvbiBxdWFuZG8gYWJl'
    'cnRvICovfQogICAgICAgIHtvcGVuICYmICgKICAgICAgICAgIDxidXR0b24KICAgICAgICAgICAg'
    'b25DbGljaz17KCkgPT4geyBzZXRPcGVuKGZhbHNlKTsgc2V0TWVzc2FnZXMoW10pOyB9fQogICAg'
    'ICAgICAgICBzdHlsZT17ewogICAgICAgICAgICAgIHBvc2l0aW9uOiAnYWJzb2x1dGUnLAogICAg'
    'ICAgICAgICAgIHRvcDogLTM2LAogICAgICAgICAgICAgIHJpZ2h0OiAwLAogICAgICAgICAgICAg'
    'IGJhY2tncm91bmQ6ICd0cmFuc3BhcmVudCcsCiAgICAgICAgICAgICAgYm9yZGVyOiAnbm9uZScs'
    'CiAgICAgICAgICAgICAgZm9udFNpemU6IDIyLAogICAgICAgICAgICAgIGNvbG9yOiAnIzY2Nics'
    'CiAgICAgICAgICAgICAgY3Vyc29yOiAncG9pbnRlcicsCiAgICAgICAgICAgICAgcGFkZGluZzog'
    'NCwKICAgICAgICAgICAgICBsaW5lSGVpZ2h0OiAxLAogICAgICAgICAgICB9fQogICAgICAgICAg'
    'ICBhcmlhLWxhYmVsPSJGZWNoYXIiCiAgICAgICAgICA+4pyVPC9idXR0b24+CiAgICAgICAgKX0K'
    'CiAgICAgICAgey8qIElucHV0IGJhciAqL30KICAgICAgICA8ZGl2CiAgICAgICAgICBzdHlsZT17'
    'ewogICAgICAgICAgICBkaXNwbGF5OiAnZmxleCcsCiAgICAgICAgICAgIGFsaWduSXRlbXM6ICdj'
    'ZW50ZXInLAogICAgICAgICAgICBnYXA6IDYsCiAgICAgICAgICAgIGJhY2tncm91bmQ6ICd3aGl0'
    'ZScsCiAgICAgICAgICAgIGJvcmRlcjogJzFweCBzb2xpZCByZ2JhKDc0LCAxMjQsIDg5LCAwLjM1'
    'KScsCiAgICAgICAgICAgIGJvcmRlclJhZGl1czogOTk5LAogICAgICAgICAgICBwYWRkaW5nOiAn'
    'OHB4IDhweCA4cHggMTRweCcsCiAgICAgICAgICAgIGJveFNoYWRvdzogJzAgOHB4IDI0cHggcmdi'
    'YSgyNywgNTgsIDMzLCAwLjEwKSwgMCAycHggNnB4IHJnYmEoMjcsIDU4LCAzMywgMC4wNiknLAog'
    'ICAgICAgICAgfX0KICAgICAgICA+CiAgICAgICAgICB7LyogTWljcm9waG9uZSAqL30KICAgICAg'
    'ICAgIDxidXR0b24KICAgICAgICAgICAgdHlwZT0iYnV0dG9uIgogICAgICAgICAgICB0aXRsZT0i'
    'w4F1ZGlvIChlbSBicmV2ZSkiCiAgICAgICAgICAgIHN0eWxlPXtpY29uQnRuU3R5bGV9CiAgICAg'
    'ICAgICAgIG9uQ2xpY2s9eygpID0+IHt9fQogICAgICAgICAgPgogICAgICAgICAgICA8c3ZnIHdp'
    'ZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJv'
    'a2U9IiMxQjNBMjEiIHN0cm9rZVdpZHRoPSIxLjgiIHN0cm9rZUxpbmVjYXA9InJvdW5kIiBzdHJv'
    'a2VMaW5lam9pbj0icm91bmQiPgogICAgICAgICAgICAgIDxwYXRoIGQ9Ik0xMiAxYTMgMyAwIDAg'
    'MC0zIDN2OGEzIDMgMCAwIDAgNiAwVjRhMyAzIDAgMCAwLTMtM3oiLz4KICAgICAgICAgICAgICA8'
    'cGF0aCBkPSJNMTkgMTB2MmE3IDcgMCAwIDEtMTQgMHYtMiIvPgogICAgICAgICAgICAgIDxsaW5l'
    'IHgxPSIxMiIgeTE9IjE5IiB4Mj0iMTIiIHkyPSIyMyIvPgogICAgICAgICAgICAgIDxsaW5lIHgx'
    'PSI4IiB5MT0iMjMiIHgyPSIxNiIgeTI9IjIzIi8+CiAgICAgICAgICAgIDwvc3ZnPgogICAgICAg'
    'ICAgPC9idXR0b24+CgogICAgICAgICAgey8qIENsaXAgLyBhdHRhY2ggKi99CiAgICAgICAgICA8'
    'YnV0dG9uCiAgICAgICAgICAgIHR5cGU9ImJ1dHRvbiIKICAgICAgICAgICAgdGl0bGU9IkFuZXhh'
    'ciAoZW0gYnJldmUpIgogICAgICAgICAgICBzdHlsZT17aWNvbkJ0blN0eWxlfQogICAgICAgICAg'
    'ICBvbkNsaWNrPXsoKSA9PiB7fX0KICAgICAgICAgID4KICAgICAgICAgICAgPHN2ZyB3aWR0aD0i'
    'MTgiIGhlaWdodD0iMTgiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIj'
    'MUIzQTIxIiBzdHJva2VXaWR0aD0iMS44IiBzdHJva2VMaW5lY2FwPSJyb3VuZCIgc3Ryb2tlTGlu'
    'ZWpvaW49InJvdW5kIj4KICAgICAgICAgICAgICA8cGF0aCBkPSJNMjEuNDQgMTEuMDVsLTkuMTkg'
    'OS4xOWE2IDYgMCAwIDEtOC40OS04LjQ5bDkuMTktOS4xOWE0IDQgMCAwIDEgNS42NiA1LjY2bC05'
    'LjIgOS4xOWEyIDIgMCAwIDEtMi44My0yLjgzbDguNDktOC40OCIvPgogICAgICAgICAgICA8L3N2'
    'Zz4KICAgICAgICAgIDwvYnV0dG9uPgoKICAgICAgICAgIHsvKiBJbnB1dCAqL30KICAgICAgICAg'
    'IDxpbnB1dAogICAgICAgICAgICByZWY9e2lucHV0UmVmfQogICAgICAgICAgICB0eXBlPSJ0ZXh0'
    'IgogICAgICAgICAgICB2YWx1ZT17aW5wdXR9CiAgICAgICAgICAgIG9uQ2hhbmdlPXsoZSkgPT4g'
    'c2V0SW5wdXQoZS50YXJnZXQudmFsdWUpfQogICAgICAgICAgICBvbktleURvd249eyhlKSA9PiB7'
    'IGlmIChlLmtleSA9PT0gJ0VudGVyJykgc2VuZCgpOyB9fQogICAgICAgICAgICBvbkZvY3VzPXso'
    'KSA9PiB7IGlmICghb3Blbikgc2V0T3Blbih0cnVlKTsgfX0KICAgICAgICAgICAgcGxhY2Vob2xk'
    'ZXI9IkFzayBQbGFudGEgYW55dGhpbmcgYWJvdXQgeW91ciBidWlsZGluZ+KApiIKICAgICAgICAg'
    'ICAgZGlzYWJsZWQ9e3NlbmRpbmd9CiAgICAgICAgICAgIHN0eWxlPXt7CiAgICAgICAgICAgICAg'
    'ZmxleDogMSwKICAgICAgICAgICAgICBiYWNrZ3JvdW5kOiAndHJhbnNwYXJlbnQnLAogICAgICAg'
    'ICAgICAgIGJvcmRlcjogJ25vbmUnLAogICAgICAgICAgICAgIG91dGxpbmU6ICdub25lJywKICAg'
    'ICAgICAgICAgICBwYWRkaW5nOiAnOHB4IDhweCcsCiAgICAgICAgICAgICAgZm9udFNpemU6IDE1'
    'LAogICAgICAgICAgICAgIGNvbG9yOiAnIzFBMUExQScsCiAgICAgICAgICAgICAgbWluV2lkdGg6'
    'IDAsCiAgICAgICAgICAgIH19CiAgICAgICAgICAvPgoKICAgICAgICAgIHsvKiBTZW5kIGJ1dHRv'
    'biAqL30KICAgICAgICAgIDxidXR0b24KICAgICAgICAgICAgb25DbGljaz17KCkgPT4gc2VuZCgp'
    'fQogICAgICAgICAgICBkaXNhYmxlZD17IWlucHV0LnRyaW0oKSB8fCBzZW5kaW5nfQogICAgICAg'
    'ICAgICBzdHlsZT17ewogICAgICAgICAgICAgIGJhY2tncm91bmQ6IGlucHV0LnRyaW0oKSA/ICcj'
    'MUIzQTIxJyA6ICcjRThFNUREJywKICAgICAgICAgICAgICBjb2xvcjogaW5wdXQudHJpbSgpID8g'
    'J3doaXRlJyA6ICcjOTk5JywKICAgICAgICAgICAgICBib3JkZXI6ICdub25lJywKICAgICAgICAg'
    'ICAgICBib3JkZXJSYWRpdXM6ICc1MCUnLAogICAgICAgICAgICAgIHdpZHRoOiAzNiwKICAgICAg'
    'ICAgICAgICBoZWlnaHQ6IDM2LAogICAgICAgICAgICAgIGN1cnNvcjogaW5wdXQudHJpbSgpICYm'
    'ICFzZW5kaW5nID8gJ3BvaW50ZXInIDogJ2RlZmF1bHQnLAogICAgICAgICAgICAgIHRyYW5zaXRp'
    'b246ICdiYWNrZ3JvdW5kIDAuMTVzJywKICAgICAgICAgICAgICBkaXNwbGF5OiAnZmxleCcsCiAg'
    'ICAgICAgICAgICAgYWxpZ25JdGVtczogJ2NlbnRlcicsCiAgICAgICAgICAgICAganVzdGlmeUNv'
    'bnRlbnQ6ICdjZW50ZXInLAogICAgICAgICAgICAgIGZsZXhTaHJpbms6IDAsCiAgICAgICAgICAg'
    'IH19CiAgICAgICAgICAgIGFyaWEtbGFiZWw9IkVudmlhciIKICAgICAgICAgID4KICAgICAgICAg'
    'ICAgPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0i'
    'bm9uZSIgc3Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZVdpZHRoPSIyLjIiIHN0cm9rZUxpbmVj'
    'YXA9InJvdW5kIiBzdHJva2VMaW5lam9pbj0icm91bmQiPgogICAgICAgICAgICAgIDxsaW5lIHgx'
    'PSIxMiIgeTE9IjE5IiB4Mj0iMTIiIHkyPSI1Ii8+CiAgICAgICAgICAgICAgPHBvbHlsaW5lIHBv'
    'aW50cz0iNSAxMiAxMiA1IDE5IDEyIi8+CiAgICAgICAgICAgIDwvc3ZnPgogICAgICAgICAgPC9i'
    'dXR0b24+CiAgICAgICAgPC9kaXY+CgogICAgICAgIHsvKiBTdWJ0bGUgZm9vdGVyIG5vdGUgKi99'
    'CiAgICAgICAgPGRpdgogICAgICAgICAgc3R5bGU9e3sKICAgICAgICAgICAgdGV4dEFsaWduOiAn'
    'Y2VudGVyJywKICAgICAgICAgICAgbWFyZ2luVG9wOiA4LAogICAgICAgICAgICBmb250U2l6ZTog'
    'MTEsCiAgICAgICAgICAgIGNvbG9yOiAnIzg4OCcsCiAgICAgICAgICAgIGZvbnRGYW1pbHk6ICd2'
    'YXIoLS1mb250LW1vbm8pLCBtb25vc3BhY2UnLAogICAgICAgICAgICBsZXR0ZXJTcGFjaW5nOiAn'
    'MC4wNGVtJywKICAgICAgICAgIH19CiAgICAgICAgPgogICAgICAgICAgUGxhbnRhT1MgY2FuIG1h'
    'a2UgbWlzdGFrZXMKICAgICAgICA8L2Rpdj4KICAgICAgPC9kaXY+CgogICAgICA8c3R5bGUganN4'
    'IGdsb2JhbD57YAogICAgICAgIEBrZXlmcmFtZXMgcGxhbnRhLWJsaW5rIHsKICAgICAgICAgIDAl'
    'LCAxMDAlIHsgb3BhY2l0eTogMC4zOyB9CiAgICAgICAgICA1MCUgeyBvcGFjaXR5OiAxOyB9CiAg'
    'ICAgICAgfQogICAgICBgfTwvc3R5bGU+CiAgICA8Lz4KICApOwp9Cgpjb25zdCBpY29uQnRuU3R5'
    'bGU6IFJlYWN0LkNTU1Byb3BlcnRpZXMgPSB7CiAgYmFja2dyb3VuZDogJ3RyYW5zcGFyZW50JywK'
    'ICBib3JkZXI6ICdub25lJywKICB3aWR0aDogMzIsCiAgaGVpZ2h0OiAzMiwKICBib3JkZXJSYWRp'
    'dXM6ICc1MCUnLAogIGRpc3BsYXk6ICdmbGV4JywKICBhbGlnbkl0ZW1zOiAnY2VudGVyJywKICBq'
    'dXN0aWZ5Q29udGVudDogJ2NlbnRlcicsCiAgY3Vyc29yOiAncG9pbnRlcicsCiAgZmxleFNocmlu'
    'azogMCwKICBwYWRkaW5nOiAwLAp9Owo='
)

def sec(m): print(); print("="*68); print("  "+m); print("="*68)

def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0

def find_latest_backup(folder, pattern):
    """Procura o backup .bak.v10.* mais recente."""
    matches = list(folder.glob(pattern))
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]

def restore_old_topbar(root, stamp):
    """Restaura o TopBar antigo dos backups e adiciona 3 novos links."""
    topbar = root / "frontend" / "components" / "v2" / "TopBar.tsx"
    folder = topbar.parent
    # O backup mais antigo deve ser o original (antes do v10)
    backups = list(folder.glob("TopBar.tsx.bak.v10.*"))
    if not backups:
        print("  WARN: nenhum backup TopBar encontrado — vou tentar v9, v8")
        backups = list(folder.glob("TopBar.tsx.bak.v9.*"))
    if not backups:
        backups = list(folder.glob("TopBar.tsx.bak.*"))
    if not backups:
        print("  ERRO: nenhum backup do TopBar encontrado")
        return False
    
    # O mais antigo = o original (foi feito antes do v9 substituir)
    backups.sort(key=lambda p: p.stat().st_mtime)
    oldest = backups[0]
    print(f"  i restaurar TopBar a partir de {oldest.name}")
    
    # Backup actual antes de substituir
    if topbar.exists():
        shutil.copy2(topbar, topbar.with_suffix(f".tsx.bak.v10b.{stamp}"))
    
    content = oldest.read_text()
    
    # Adicionar links novos se ainda não estiverem lá
    if "/v2/scor" not in content:
        # Procurar { href: '/v2/chat', label: 'Chat AI' }
        anc = "{ href: '/v2/chat', label: 'Chat AI' }"
        if anc in content:
            new_links = (
                "{ href: '/v2/twin', label: 'Digital Twin' },\n  "
                "{ href: '/v2/scor', label: 'SCOR' },\n  "
                "{ href: '/v2/cleaning', label: 'Limpeza' },\n  "
                "{ href: '/v2/pipelines', label: 'Pipelines' },\n  "
                + anc
            )
            # Remover Twin existente se houver para não duplicar
            content = re.sub(r"\{\s*href:\s*'/v2/twin'[^}]+\},?\s*", "", content)
            content = content.replace(anc, new_links, 1)
            print("  OK 4 links adicionados ao TopBar antigo")
        else:
            print("  WARN: anchor Chat AI não encontrado no TopBar antigo")
    
    topbar.write_text(content)
    return True

def patch_layout(root, stamp):
    """Remove LiveTerminal + Substitui PlantaChatbot por PlantaSearchBar."""
    layout = root / "frontend" / "app" / "v2" / "layout.tsx"
    if not layout.exists():
        print("  ERRO: layout.tsx não encontrado")
        return False
    
    shutil.copy2(layout, layout.with_suffix(f".tsx.bak.v10b.{stamp}"))
    content = layout.read_text()
    original = content
    
    # 1. Remover import e uso do LiveTerminal
    content = re.sub(r"^import\s+LiveTerminal\s+from\s+['\"][^'\"]+['\"];?\s*\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"<LiveTerminal\s*/>\s*", "", content)
    content = re.sub(r"<LiveTerminal>\s*</LiveTerminal>\s*", "", content)
    
    # 2. Substituir import de PlantaChatbot por PlantaSearchBar
    content = re.sub(
        r"import\s+PlantaChatbot\s+from\s+['\"](@/components/v2/)PlantaChatbot['\"];?",
        "import PlantaSearchBar from '\\1PlantaSearchBar';",
        content,
    )
    # E usage
    content = content.replace("<PlantaChatbot />", "<PlantaSearchBar />")
    content = content.replace("<PlantaChatbot/>", "<PlantaSearchBar />")
    
    # 3. Se PlantaSearchBar não estiver lá, adicionar
    if "PlantaSearchBar" not in content:
        # Inserir import depois de outros imports
        if "import" in content:
            idx = content.find("\n", content.find("import"))
            content = (content[:idx] + 
                       "\nimport PlantaSearchBar from '@/components/v2/PlantaSearchBar';" +
                       content[idx:])
        # Render dentro de <main> antes de fechar
        if "{children}" in content:
            content = content.replace("{children}", "{children}\n      <PlantaSearchBar />", 1)
    
    if content == original:
        print("  i layout.tsx sem mudanças necessárias")
    else:
        layout.write_text(content)
        print("  OK layout.tsx: LiveTerminal removido, PlantaChatbot → PlantaSearchBar")
    return True

def main():
    root = Path.cwd()
    if not (root / "app").exists() or not (root / "frontend").exists():
        print("ERRO: corre a partir de ~/planta_rock4"); sys.exit(1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    sec("1. ESCREVER PlantaSearchBar.tsx (novo)")
    searchbar = root / "frontend" / "components" / "v2" / "PlantaSearchBar.tsx"
    searchbar.parent.mkdir(parents=True, exist_ok=True)
    if searchbar.exists():
        shutil.copy2(searchbar, searchbar.with_suffix(f".tsx.bak.v10b.{stamp}"))
    data = base64.b64decode("".join(SEARCHBAR_B64))
    searchbar.write_bytes(data)
    print(f"  OK PlantaSearchBar.tsx ({len(data)} B)")
    
    sec("2. RESTAURAR TopBar antigo + adicionar 4 links")
    restore_old_topbar(root, stamp)
    
    sec("3. PATCH layout.tsx (remover LiveTerminal + PlantaChatbot→PlantaSearchBar)")
    patch_layout(root, stamp)
    
    sec("4. APAGAR PlantaChatbot (não usado)")
    old_chatbot = root / "frontend" / "components" / "v2" / "PlantaChatbot.tsx"
    if old_chatbot.exists():
        shutil.copy2(old_chatbot, old_chatbot.with_suffix(f".tsx.bak.v10b.{stamp}"))
        old_chatbot.unlink()
        print("  OK PlantaChatbot.tsx apagado (backup guardado)")
    
    sec("5. GIT COMMIT + PUSH")
    run("git add app/ frontend/", cwd=str(root))
    run("git status --short | grep -v '.bak' | head -20", cwd=str(root))
    run('git commit -m "fix(v10b): remove terminal preto + restaurar TopBar antigo + searchbar estilo Claude"', cwd=str(root))
    run("git push", cwd=str(root))
    
    sec("6. PRÓXIMO PASSO")
    print("""
  Aguarda Vercel rebuildar (~1.5min). Depois CMD+SHIFT+R em qualquer página /v2.
  Vais ver:
    - Barra preta no fundo: REMOVIDA
    - Em vez do círculo verde 💬, agora tens uma SEARCHBAR grande:
      "Ask Planta anything about your building..." com 🎤 + 📎 + botão ↑
    - TopBar restaurado ao design original com links extra: Limpeza, SCOR, Pipelines
""")

if __name__ == "__main__":
    main()

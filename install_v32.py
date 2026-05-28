#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_v32 — /sensors 100% wow (sem scroll) + /pipelines so-admin + nav limpo

1. /v2/sensors: full-bleed 100vh, grelha 4x2 dos 8 clusters ao vivo
   (ocupacao, fila, espera, confianca, nos), KPIs de rede no topo.
   Conta SO pessoas e fluxos. Sem scroll. Paleta v12. lucide icons.
2. /v2/pipelines: protegida por chave de admin (?key=planta-ops, guardada
   em localStorage). Sem chave -> "Acesso restrito". O conteudo actual e
   movido para _content.tsx e passa a ser renderizado so apos auth.
3. TopBar: remove o item "Pipelines" do menu publico.
"""

import base64, os, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path
os.environ["PATH"] = ":".join(["/usr/bin","/bin","/usr/sbin","/sbin","/usr/local/bin","/opt/homebrew/bin",os.environ.get("PATH","")])

SENSORS_B64 = (
    'J3VzZSBjbGllbnQnOwoKaW1wb3J0IHsgdXNlRWZmZWN0LCB1c2VNZW1vLCB1c2VTdGF0ZSB9IGZy'
    'b20gJ3JlYWN0JzsKaW1wb3J0IHsKICBhcGksCiAgdHlwZSBCYWNrZW5kU2Vuc29yLAogIHR5cGUg'
    'U2Vuc29yc1N1bW1hcnksCn0gZnJvbSAnQC9saWIvdjItYXBpJzsKaW1wb3J0IHsgdXNlTGl2ZSwg'
    'dHlwZSBDbHVzdGVyUGF5bG9hZCB9IGZyb20gJ0AvY29tcG9uZW50cy92Mi9MaXZlQ29udGV4dCc7'
    'CmltcG9ydCB7CiAgV2lmaSwgV2lmaU9mZiwgUmFkaW8sIEFjdGl2aXR5LCBTaGllbGRDaGVjaywg'
    'QWxlcnRUcmlhbmdsZSwKfSBmcm9tICdsdWNpZGUtcmVhY3QnOwoKY29uc3QgUkVGUkVTSF9NUyA9'
    'IDE1XzAwMDsKCmNvbnN0IENMVVNURVJfWk9ORTogUmVjb3JkPHN0cmluZywgc3RyaW5nPiA9IHsK'
    'ICAnd2MtMDEnOiAnUG9ydGFsIE5vcnRlJywgJ3djLTAyJzogJ0NlbnRyYWwnLCAnd2MtMDMnOiAn'
    'UG9ydMOjbycsICd3Yy0wNCc6ICdDdW1lYWRhJywKICAnd2MtMDUnOiAnUG9ydMOjbycsICd3Yy0w'
    'Nic6ICdDZW50cmFsJywgJ3djLTA3JzogJ0xvY2tlcnMnLCAnd2MtMDgnOiAnRXh0ZXJpb3InLAp9'
    'OwoKdHlwZSBTdGF0ZSA9ICdjYWxtbycgfCAnYWN0aXZvJyB8ICdpbnRlbnNvJzsKCmZ1bmN0aW9u'
    'IG9jY1N0YXRlKG9jYzogbnVtYmVyKTogU3RhdGUgewogIGlmIChvY2MgPj0gODApIHJldHVybiAn'
    'aW50ZW5zbyc7CiAgaWYgKG9jYyA+PSA1NSkgcmV0dXJuICdhY3Rpdm8nOwogIHJldHVybiAnY2Fs'
    'bW8nOwp9CmNvbnN0IFNUQVRFX0NPTE9SOiBSZWNvcmQ8U3RhdGUsIHN0cmluZz4gPSB7CiAgY2Fs'
    'bW86ICd2YXIoLS1ncmVlbiwgIzFCM0EyMSknLAogIGFjdGl2bzogJ3ZhcigtLWdyZWVuLXNvZnQs'
    'ICM0QTdDNTkpJywKICBpbnRlbnNvOiAndmFyKC0tYW1iZXIsICNDMjVBMUEpJywKfTsKY29uc3Qg'
    'U1RBVEVfTEFCRUw6IFJlY29yZDxTdGF0ZSwgeyBwdDogc3RyaW5nOyBlbjogc3RyaW5nIH0+ID0g'
    'ewogIGNhbG1vOiB7IHB0OiAnQ2FsbW8nLCBlbjogJ0NhbG0nIH0sCiAgYWN0aXZvOiB7IHB0OiAn'
    'QWN0aXZvJywgZW46ICdBY3RpdmUnIH0sCiAgaW50ZW5zbzogeyBwdDogJ0ludGVuc28nLCBlbjog'
    'J0J1c3knIH0sCn07CgpmdW5jdGlvbiBjbHVzdGVyTnVtKGlkOiBzdHJpbmcpOiBzdHJpbmcgewog'
    'IGNvbnN0IG0gPSBpZC5tYXRjaCgvKFxkKykvKTsKICByZXR1cm4gbSA/IG1bMV0ucGFkU3RhcnQo'
    'MiwgJzAnKSA6IGlkLnRvVXBwZXJDYXNlKCk7Cn0KCmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFNl'
    'bnNvcnNQYWdlKCkgewogIGNvbnN0IHsgc25hcHNob3QsIGNvbm5lY3Rpb24gfSA9IHVzZUxpdmUo'
    'KTsKICBjb25zdCBbc2Vuc29ycywgc2V0U2Vuc29yc10gPSB1c2VTdGF0ZTxCYWNrZW5kU2Vuc29y'
    'W10+KFtdKTsKICBjb25zdCBbc3VtbWFyeSwgc2V0U3VtbWFyeV0gPSB1c2VTdGF0ZTxTZW5zb3Jz'
    'U3VtbWFyeSB8IG51bGw+KG51bGwpOwoKICB1c2VFZmZlY3QoKCkgPT4gewogICAgbGV0IGNhbmNl'
    'bGxlZCA9IGZhbHNlOwogICAgY29uc3QgdGljayA9IGFzeW5jICgpID0+IHsKICAgICAgdHJ5IHsK'
    'ICAgICAgICBjb25zdCBbbGlzdCwgc3VtXSA9IGF3YWl0IFByb21pc2UuYWxsKFthcGkuc2Vuc29y'
    'cygpLCBhcGkuc2Vuc29yc1N1bW1hcnkoKV0pOwogICAgICAgIGlmIChjYW5jZWxsZWQpIHJldHVy'
    'bjsKICAgICAgICBzZXRTZW5zb3JzKGxpc3QpOwogICAgICAgIHNldFN1bW1hcnkoc3VtKTsKICAg'
    'ICAgfSBjYXRjaCB7IC8qIG1hbnTDqW0gw7psdGltbyBlc3RhZG8gKi8gfQogICAgfTsKICAgIHRp'
    'Y2soKTsKICAgIGNvbnN0IGl2ID0gc2V0SW50ZXJ2YWwodGljaywgUkVGUkVTSF9NUyk7CiAgICBy'
    'ZXR1cm4gKCkgPT4geyBjYW5jZWxsZWQgPSB0cnVlOyBjbGVhckludGVydmFsKGl2KTsgfTsKICB9'
    'LCBbXSk7CgogIC8vIG7Ds3MgcG9yIGNsdXN0ZXIKICBjb25zdCBzZW5zb3JzQnlDbHVzdGVyID0g'
    'dXNlTWVtbygoKSA9PiB7CiAgICBjb25zdCBtID0gbmV3IE1hcDxzdHJpbmcsIEJhY2tlbmRTZW5z'
    'b3JbXT4oKTsKICAgIGZvciAoY29uc3QgcyBvZiBzZW5zb3JzKSB7CiAgICAgIGNvbnN0IGsgPSAo'
    'cy5jbHVzdGVyX2lkIHx8ICcnKS50b0xvd2VyQ2FzZSgpOwogICAgICBpZiAoIW0uaGFzKGspKSBt'
    'LnNldChrLCBbXSk7CiAgICAgIG0uZ2V0KGspIS5wdXNoKHMpOwogICAgfQogICAgcmV0dXJuIG07'
    'CiAgfSwgW3NlbnNvcnNdKTsKCiAgY29uc3QgbGl2ZUJ5Q2x1c3RlciA9IHVzZU1lbW8oKCkgPT4g'
    'ewogICAgY29uc3QgbSA9IG5ldyBNYXA8c3RyaW5nLCBDbHVzdGVyUGF5bG9hZD4oKTsKICAgIGZv'
    'ciAoY29uc3QgYyBvZiBzbmFwc2hvdD8uY2x1c3RlcnMgPz8gW10pIG0uc2V0KGMuY2x1c3Rlcl9p'
    'ZC50b0xvd2VyQ2FzZSgpLCBjKTsKICAgIHJldHVybiBtOwogIH0sIFtzbmFwc2hvdF0pOwoKICAv'
    'LyBsaXN0YSBjYW7Ds25pY2EgZG9zIDgKICBjb25zdCBjbHVzdGVySWRzID0gdXNlTWVtbygoKSA9'
    'PiB7CiAgICBjb25zdCBmcm9tTGl2ZSA9IChzbmFwc2hvdD8uZXhwZWN0ZWRfY2x1c3RlcnMgPz8g'
    'W10pLm1hcCgoYykgPT4gYy50b0xvd2VyQ2FzZSgpKTsKICAgIGNvbnN0IGJhc2UgPSBmcm9tTGl2'
    'ZS5sZW5ndGggPyBmcm9tTGl2ZSA6IFsnd2MtMDEnLCd3Yy0wMicsJ3djLTAzJywnd2MtMDQnLCd3'
    'Yy0wNScsJ3djLTA2Jywnd2MtMDcnLCd3Yy0wOCddOwogICAgcmV0dXJuIGJhc2Uuc2xpY2UoMCwg'
    'OCk7CiAgfSwgW3NuYXBzaG90XSk7CgogIC8vIEtQSXMgZGUgcmVkZQogIGNvbnN0IHRvdGFsTm9k'
    'ZXMgPSBzZW5zb3JzLmxlbmd0aCB8fCAoc3VtbWFyeT8udG90YWwgPz8gMCk7CiAgY29uc3Qgb25s'
    'aW5lTm9kZXMgPSBzZW5zb3JzLmZpbHRlcigocykgPT4gdHJ1ZSkubGVuZ3RoOyAvLyBzYcO6ZGUg'
    'ZGV0YWxoYWRhIHZlbSBkbyBoZWFsdGggbWFwIGFiYWl4bwogIGNvbnN0IGhlYWx0aE1hcCA9IHN1'
    'bW1hcnk/LmhlYWx0aCA/PyB7fTsKICBjb25zdCBvbmxpbmUgPSBoZWFsdGhNYXBbJ29ubGluZSdd'
    'ID8/IG9ubGluZU5vZGVzOwogIGNvbnN0IGRlZ3JhZGVkID0gKGhlYWx0aE1hcFsnb2ZmbGluZSdd'
    'ID8/IDApICsgKGhlYWx0aE1hcFsnZGVncmFkZWQnXSA/PyAwKTsKICBjb25zdCBjb3ZlcmFnZSA9'
    'IHRvdGFsTm9kZXMgPiAwID8gTWF0aC5yb3VuZCgob25saW5lIC8gdG90YWxOb2RlcykgKiAxMDAp'
    'IDogMTAwOwogIGNvbnN0IGxpdmUgPSBjb25uZWN0aW9uID09PSAnc3NlJyB8fCBjb25uZWN0aW9u'
    'ID09PSAncG9sbGluZyc7CgogIHJldHVybiAoCiAgICA8ZGl2IGNsYXNzTmFtZT0ic3gtcm9vdCI+'
    'CiAgICAgIHsvKiBGYWl4YSBkZSBLUElzICovfQogICAgICA8aGVhZGVyIGNsYXNzTmFtZT0ic3gt'
    'aGVhZCI+CiAgICAgICAgPGRpdiBjbGFzc05hbWU9InN4LXRpdGxlLXdyYXAiPgogICAgICAgICAg'
    'PGRpdiBjbGFzc05hbWU9InN4LWV5ZWJyb3ciPlBsYW50YU9TIMK3IFJlZGUgZGUgc2Vuc29yZXM8'
    'L2Rpdj4KICAgICAgICAgIDxoMSBjbGFzc05hbWU9InN4LXRpdGxlIj5TZW5zb3JlcyA8c3BhbiBj'
    'bGFzc05hbWU9InN4LXN1YiI+U2Vuc29yczwvc3Bhbj48L2gxPgogICAgICAgIDwvZGl2PgogICAg'
    'ICAgIDxkaXYgY2xhc3NOYW1lPSJzeC1rcGlzIj4KICAgICAgICAgIDxLcGkgaWNvbj17PFJhZGlv'
    'IHNpemU9ezE4fSBzdHJva2VXaWR0aD17MS41fSAvPn0gbGFiZWw9Ik7Ds3MiIHZhbHVlPXtTdHJp'
    'bmcodG90YWxOb2Rlcyl9IC8+CiAgICAgICAgICA8S3BpIGljb249ezxTaGllbGRDaGVjayBzaXpl'
    'PXsxOH0gc3Ryb2tlV2lkdGg9ezEuNX0gLz59IGxhYmVsPSJDb2JlcnR1cmEiIHZhbHVlPXtgJHtj'
    'b3ZlcmFnZX0lYH0gdG9uZT17Y292ZXJhZ2UgPj0gOTAgPyAnb2snIDogJ3dhcm4nfSAvPgogICAg'
    'ICAgICAgPEtwaSBpY29uPXtvbmxpbmUgPiAwID8gPFdpZmkgc2l6ZT17MTh9IHN0cm9rZVdpZHRo'
    'PXsxLjV9IC8+IDogPFdpZmlPZmYgc2l6ZT17MTh9IHN0cm9rZVdpZHRoPXsxLjV9IC8+fSBsYWJl'
    'bD0iT25saW5lIiB2YWx1ZT17U3RyaW5nKG9ubGluZSl9IC8+CiAgICAgICAgICA8S3BpIGljb249'
    'ezxBY3Rpdml0eSBzaXplPXsxOH0gc3Ryb2tlV2lkdGg9ezEuNX0gLz59IGxhYmVsPSJTaW5hbCIg'
    'dmFsdWU9e2xpdmUgPyAnYW8gdml2bycgOiAn4oCUJ30gdG9uZT17bGl2ZSA/ICdvaycgOiAnd2Fy'
    'bid9IGxpdmU9e2xpdmV9IC8+CiAgICAgICAgPC9kaXY+CiAgICAgIDwvaGVhZGVyPgoKICAgICAg'
    'ey8qIEdyZWxoYSA0w5cyIGRvcyA4IGNsdXN0ZXJzIOKAlCAxMDB2aCwgc2VtIHNjcm9sbCAqL30K'
    'ICAgICAgPGRpdiBjbGFzc05hbWU9InN4LWdyaWQiPgogICAgICAgIHtjbHVzdGVySWRzLm1hcCgo'
    'Y2lkKSA9PiB7CiAgICAgICAgICBjb25zdCBub2RlcyA9IHNlbnNvcnNCeUNsdXN0ZXIuZ2V0KGNp'
    'ZCkgPz8gW107CiAgICAgICAgICBjb25zdCBsYyA9IGxpdmVCeUNsdXN0ZXIuZ2V0KGNpZCk7CiAg'
    'ICAgICAgICBjb25zdCBwID0gbGM/LnBhcmFtczsKICAgICAgICAgIGNvbnN0IG9jYyA9IE1hdGgu'
    'cm91bmQocD8ub2N1cGFjYW9faW5zdGFudGFuZWEgPz8gMCk7CiAgICAgICAgICBjb25zdCBzdCA9'
    'IG9jY1N0YXRlKG9jYyk7CiAgICAgICAgICBjb25zdCBjb25mID0gTWF0aC5yb3VuZCgocD8uY29u'
    'ZmlhbmNhX2NydXphZGEgPz8gMCkgKiAxMDApOwogICAgICAgICAgY29uc3QgZmlsYSA9IHA/LmZp'
    'bGFfYXR1YWwgPz8gMDsKICAgICAgICAgIGNvbnN0IGVzcGVyYSA9IHA/LnRlbXBvX2VzcGVyYV9t'
    'aW4gPz8gMDsKICAgICAgICAgIGNvbnN0IHVuaXNleCA9IHA/LmlzX3VuaXNzZXg7CiAgICAgICAg'
    'ICBjb25zdCBub2RlT25saW5lID0gbm9kZXMubGVuZ3RoOwogICAgICAgICAgY29uc3QgY29sb3Ig'
    'PSBTVEFURV9DT0xPUltzdF07CgogICAgICAgICAgcmV0dXJuICgKICAgICAgICAgICAgPGFydGlj'
    'bGUga2V5PXtjaWR9IGNsYXNzTmFtZT0ic3gtY2FyZCIgc3R5bGU9e3sgWyctLWFjY2VudCcgYXMg'
    'YW55XTogY29sb3IgfX0+CiAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9InN4LWNhcmQtdG9w'
    'Ij4KICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPSJzeC1jYXJkLWlkIj4KICAgICAgICAg'
    'ICAgICAgICAgPHNwYW4gY2xhc3NOYW1lPSJzeC13YyI+V0Mte2NsdXN0ZXJOdW0oY2lkKX08L3Nw'
    'YW4+CiAgICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzTmFtZT0ic3gtem9uZSI+e3VuaXNleCA/'
    'ICd1bmlzc2V4bycgOiBDTFVTVEVSX1pPTkVbY2lkXSA/PyAnJ308L3NwYW4+CiAgICAgICAgICAg'
    'ICAgICA8L2Rpdj4KICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPSJzeC1zdGF0ZSIgc3R5'
    'bGU9e3sgY29sb3IgfX0+CiAgICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzTmFtZT0ic3gtZG90'
    'IiBzdHlsZT17eyBiYWNrZ3JvdW5kOiBjb2xvciB9fSAvPgogICAgICAgICAgICAgICAgICB7U1RB'
    'VEVfTEFCRUxbc3RdLnB0fQogICAgICAgICAgICAgICAgPC9kaXY+CiAgICAgICAgICAgICAgPC9k'
    'aXY+CgogICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPSJzeC1vY2MiPgogICAgICAgICAgICAg'
    'ICAgPHNwYW4gY2xhc3NOYW1lPSJzeC1vY2MtbnVtIiBzdHlsZT17eyBjb2xvciB9fT57b2NjfTwv'
    'c3Bhbj4KICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzTmFtZT0ic3gtb2NjLXBjdCI+JTwvc3Bh'
    'bj4KICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzTmFtZT0ic3gtb2NjLWNhcCI+b2N1cGHDp8Oj'
    'bzwvc3Bhbj4KICAgICAgICAgICAgICA8L2Rpdj4KCiAgICAgICAgICAgICAgey8qIGJhcnJhIGRl'
    'IG9jdXBhw6fDo28gKi99CiAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9InN4LWJhciI+CiAg'
    'ICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT0ic3gtYmFyLWZpbGwiIHN0eWxlPXt7IHdpZHRo'
    'OiBgJHtNYXRoLm1pbigxMDAsIG9jYyl9JWAsIGJhY2tncm91bmQ6IGNvbG9yIH19IC8+CiAgICAg'
    'ICAgICAgICAgPC9kaXY+CgogICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPSJzeC1tZXRyaWNz'
    'Ij4KICAgICAgICAgICAgICAgIDxNZXRyaWMgbGFiZWw9ImZpbGEiIHZhbHVlPXtmaWxhID4gMCA/'
    'IGAke2ZpbGF9YCA6ICfigJQnfSAvPgogICAgICAgICAgICAgICAgPE1ldHJpYyBsYWJlbD0iZXNw'
    'ZXJhIiB2YWx1ZT17ZXNwZXJhID4gMCA/IGAke2VzcGVyYX0gbWluYCA6ICdhZ29yYSd9IC8+CiAg'
    'ICAgICAgICAgICAgICA8TWV0cmljIGxhYmVsPSJuw7NzIiB2YWx1ZT17YCR7bm9kZU9ubGluZX1g'
    'fSAvPgogICAgICAgICAgICAgICAgPE1ldHJpYyBsYWJlbD0iY29uZmlhbsOnYSIgdmFsdWU9e2Ak'
    'e2NvbmZ9JWB9IHRvbmU9e2NvbmYgPj0gNzAgPyB1bmRlZmluZWQgOiAnd2Fybid9IC8+CiAgICAg'
    'ICAgICAgICAgPC9kaXY+CiAgICAgICAgICAgIDwvYXJ0aWNsZT4KICAgICAgICAgICk7CiAgICAg'
    'ICAgfSl9CiAgICAgIDwvZGl2PgoKICAgICAgPHN0eWxlIGpzeD57YAogICAgICAgIC5zeC1yb290'
    'IHsKICAgICAgICAgIHBvc2l0aW9uOiBmaXhlZDsgdG9wOiB2YXIoLS10b3BiYXItaCwgNzJweCk7'
    'IGxlZnQ6IDA7IHJpZ2h0OiAwOyBib3R0b206IDA7CiAgICAgICAgICBkaXNwbGF5OiBmbGV4OyBm'
    'bGV4LWRpcmVjdGlvbjogY29sdW1uOyBiYWNrZ3JvdW5kOiB2YXIoLS1wYXBlciwgI0ZBRkFGNyk7'
    'CiAgICAgICAgICBjb2xvcjogdmFyKC0taW5rLCAjMEQxQTBGKTsgb3ZlcmZsb3c6IGhpZGRlbjsK'
    'ICAgICAgICAgIHBhZGRpbmc6IGNsYW1wKDEycHgsMS42dncsMjJweCkgY2xhbXAoMTRweCwyLjR2'
    'dywzNHB4KSBtYXgoMTRweCwgZW52KHNhZmUtYXJlYS1pbnNldC1ib3R0b20pKTsKICAgICAgICB9'
    'CiAgICAgICAgLnN4LWhlYWQgeyBmbGV4LXNocmluazogMDsgZGlzcGxheTogZmxleDsganVzdGlm'
    'eS1jb250ZW50OiBzcGFjZS1iZXR3ZWVuOyBhbGlnbi1pdGVtczogZmxleC1lbmQ7IGdhcDogMjBw'
    'eDsgZmxleC13cmFwOiB3cmFwOyBtYXJnaW4tYm90dG9tOiBjbGFtcCgxMnB4LDEuNnZ3LDIwcHgp'
    'OyB9CiAgICAgICAgLnN4LWV5ZWJyb3cgeyBmb250LXNpemU6IDEwcHg7IGZvbnQtd2VpZ2h0OiA1'
    'MDA7IGxldHRlci1zcGFjaW5nOiAwLjE2ZW07IHRleHQtdHJhbnNmb3JtOiB1cHBlcmNhc2U7IGNv'
    'bG9yOiB2YXIoLS1pbmstZmFpbnQsIHJnYmEoMTMsMjYsMTUsMC40KSk7IH0KICAgICAgICAuc3gt'
    'dGl0bGUgeyBmb250LXNpemU6IGNsYW1wKDI0cHgsMy40dncsNDRweCk7IGZvbnQtd2VpZ2h0OiAy'
    'MDA7IGxldHRlci1zcGFjaW5nOiAtMC4wNGVtOyBsaW5lLWhlaWdodDogMTsgbWFyZ2luLXRvcDog'
    'NXB4OyB9CiAgICAgICAgLnN4LXN1YiB7IGZvbnQtc3R5bGU6IGl0YWxpYzsgZm9udC13ZWlnaHQ6'
    'IDMwMDsgZm9udC1zaXplOiAwLjVlbTsgY29sb3I6IHZhcigtLWluay1zb2Z0LCByZ2JhKDEzLDI2'
    'LDE1LDAuNTUpKTsgbGV0dGVyLXNwYWNpbmc6IC0wLjAxZW07IG1hcmdpbi1sZWZ0OiA2cHg7IH0K'
    'ICAgICAgICAuc3gta3BpcyB7IGRpc3BsYXk6IGZsZXg7IGdhcDogY2xhbXAoMTBweCwxLjR2dywy'
    'MnB4KTsgfQoKICAgICAgICAuc3gtZ3JpZCB7CiAgICAgICAgICBmbGV4OiAxOyBtaW4taGVpZ2h0'
    'OiAwOyBkaXNwbGF5OiBncmlkOwogICAgICAgICAgZ3JpZC10ZW1wbGF0ZS1jb2x1bW5zOiByZXBl'
    'YXQoNCwgMWZyKTsgZ3JpZC10ZW1wbGF0ZS1yb3dzOiByZXBlYXQoMiwgMWZyKTsKICAgICAgICAg'
    'IGdhcDogY2xhbXAoOHB4LDF2dywxNnB4KTsKICAgICAgICB9CiAgICAgICAgLnN4LWNhcmQgewog'
    'ICAgICAgICAgbWluLWhlaWdodDogMDsgbWluLXdpZHRoOiAwOyBiYWNrZ3JvdW5kOiAjZmZmOyBi'
    'b3JkZXI6IDFweCBzb2xpZCByZ2JhKDEzLDI2LDE1LDAuMDgpOwogICAgICAgICAgYm9yZGVyLXJh'
    'ZGl1czogMThweDsgcGFkZGluZzogY2xhbXAoMTJweCwxLjR2dywyMHB4KTsgZGlzcGxheTogZmxl'
    'eDsgZmxleC1kaXJlY3Rpb246IGNvbHVtbjsKICAgICAgICAgIHBvc2l0aW9uOiByZWxhdGl2ZTsg'
    'b3ZlcmZsb3c6IGhpZGRlbjsKICAgICAgICAgIGJveC1zaGFkb3c6IDAgMXB4IDJweCByZ2JhKDEz'
    'LDI2LDE1LDAuMDMpOwogICAgICAgIH0KICAgICAgICAuc3gtY2FyZDo6YmVmb3JlIHsgY29udGVu'
    'dDogJyc7IHBvc2l0aW9uOiBhYnNvbHV0ZTsgdG9wOiAwOyBsZWZ0OiAwOyByaWdodDogMDsgaGVp'
    'Z2h0OiAzcHg7IGJhY2tncm91bmQ6IHZhcigtLWFjY2VudCk7IG9wYWNpdHk6IDAuOTsgfQogICAg'
    'ICAgIC5zeC1jYXJkLXRvcCB7IGRpc3BsYXk6IGZsZXg7IGp1c3RpZnktY29udGVudDogc3BhY2Ut'
    'YmV0d2VlbjsgYWxpZ24taXRlbXM6IGZsZXgtc3RhcnQ7IGdhcDogOHB4OyB9CiAgICAgICAgLnN4'
    'LWNhcmQtaWQgeyBkaXNwbGF5OiBmbGV4OyBmbGV4LWRpcmVjdGlvbjogY29sdW1uOyBnYXA6IDFw'
    'eDsgbWluLXdpZHRoOiAwOyB9CiAgICAgICAgLnN4LXdjIHsgZm9udC1zaXplOiBjbGFtcCgxNXB4'
    'LDEuNXZ3LDIwcHgpOyBmb250LXdlaWdodDogNjAwOyBsZXR0ZXItc3BhY2luZzogLTAuMDJlbTsg'
    'fQogICAgICAgIC5zeC16b25lIHsgZm9udC1zaXplOiAxMXB4OyBmb250LXdlaWdodDogNTAwOyBj'
    'b2xvcjogdmFyKC0taW5rLWZhaW50LCByZ2JhKDEzLDI2LDE1LDAuNCkpOyBsZXR0ZXItc3BhY2lu'
    'ZzogMC4wMmVtOyB9CiAgICAgICAgLnN4LXN0YXRlIHsgZGlzcGxheTogZmxleDsgYWxpZ24taXRl'
    'bXM6IGNlbnRlcjsgZ2FwOiA1cHg7IGZvbnQtc2l6ZTogMTEuNXB4OyBmb250LXdlaWdodDogNjAw'
    'OyBsZXR0ZXItc3BhY2luZzogMC4wMWVtOyBmbGV4LXNocmluazogMDsgfQogICAgICAgIC5zeC1k'
    'b3QgeyB3aWR0aDogN3B4OyBoZWlnaHQ6IDdweDsgYm9yZGVyLXJhZGl1czogNTAlOyBhbmltYXRp'
    'b246IHN4LXB1bHNlIDEuOHMgZWFzZS1pbi1vdXQgaW5maW5pdGU7IH0KCiAgICAgICAgLnN4LW9j'
    'YyB7IGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBiYXNlbGluZTsgZ2FwOiA0cHg7IG1hcmdp'
    'bi10b3A6IGF1dG87IH0KICAgICAgICAuc3gtb2NjLW51bSB7IGZvbnQtc2l6ZTogY2xhbXAoMzRw'
    'eCw0LjR2dyw2MHB4KTsgZm9udC13ZWlnaHQ6IDIwMDsgbGV0dGVyLXNwYWNpbmc6IC0wLjA1ZW07'
    'IGxpbmUtaGVpZ2h0OiAwLjk7IGZvbnQtdmFyaWFudC1udW1lcmljOiB0YWJ1bGFyLW51bXM7IH0K'
    'ICAgICAgICAuc3gtb2NjLXBjdCB7IGZvbnQtc2l6ZTogY2xhbXAoMTVweCwxLjZ2dywyMnB4KTsg'
    'Zm9udC13ZWlnaHQ6IDMwMDsgY29sb3I6IHZhcigtLWluay1zb2Z0LCByZ2JhKDEzLDI2LDE1LDAu'
    'NTUpKTsgfQogICAgICAgIC5zeC1vY2MtY2FwIHsgZm9udC1zaXplOiAxMXB4OyBjb2xvcjogdmFy'
    'KC0taW5rLWZhaW50LCByZ2JhKDEzLDI2LDE1LDAuNCkpOyBtYXJnaW4tbGVmdDogYXV0bzsgYWxp'
    'Z24tc2VsZjogZmxleC1lbmQ7IGxldHRlci1zcGFjaW5nOiAwLjA0ZW07IHRleHQtdHJhbnNmb3Jt'
    'OiB1cHBlcmNhc2U7IH0KCiAgICAgICAgLnN4LWJhciB7IGhlaWdodDogNnB4OyBiYWNrZ3JvdW5k'
    'OiAjZjBlZWU2OyBib3JkZXItcmFkaXVzOiA0cHg7IG92ZXJmbG93OiBoaWRkZW47IG1hcmdpbjog'
    'MTBweCAwIDEycHg7IH0KICAgICAgICAuc3gtYmFyLWZpbGwgeyBoZWlnaHQ6IDEwMCU7IGJvcmRl'
    'ci1yYWRpdXM6IDRweDsgdHJhbnNpdGlvbjogd2lkdGggMC42cyBjdWJpYy1iZXppZXIoMC4yLDAu'
    'NywwLjIsMSk7IH0KCiAgICAgICAgLnN4LW1ldHJpY3MgeyBkaXNwbGF5OiBncmlkOyBncmlkLXRl'
    'bXBsYXRlLWNvbHVtbnM6IHJlcGVhdCg0LCAxZnIpOyBnYXA6IDZweDsgfQoKICAgICAgICBAa2V5'
    'ZnJhbWVzIHN4LXB1bHNlIHsgMCUsMTAwJSB7IG9wYWNpdHk6IDE7IH0gNTAlIHsgb3BhY2l0eTog'
    'MC40OyB9IH0KCiAgICAgICAgQG1lZGlhIChtYXgtd2lkdGg6IDEwMDBweCkgewogICAgICAgICAg'
    'LnN4LWdyaWQgeyBncmlkLXRlbXBsYXRlLWNvbHVtbnM6IHJlcGVhdCgyLCAxZnIpOyBncmlkLXRl'
    'bXBsYXRlLXJvd3M6IHJlcGVhdCg0LCAxZnIpOyB9CiAgICAgICAgfQogICAgICAgIEBtZWRpYSAo'
    'bWF4LXdpZHRoOiA1NjBweCkgewogICAgICAgICAgLnN4LXJvb3QgeyBvdmVyZmxvdy15OiBhdXRv'
    'OyB9CiAgICAgICAgICAuc3gtZ3JpZCB7IGdyaWQtdGVtcGxhdGUtY29sdW1uczogMWZyOyBncmlk'
    'LXRlbXBsYXRlLXJvd3M6IG5vbmU7IGdhcDogMTBweDsgfQogICAgICAgICAgLnN4LWNhcmQgeyBt'
    'aW4taGVpZ2h0OiAxNTBweDsgfQogICAgICAgICAgLnN4LWtwaXMgeyBnYXA6IDE0cHg7IH0KICAg'
    'ICAgICB9CiAgICAgICAgQG1lZGlhIChwcmVmZXJzLXJlZHVjZWQtbW90aW9uOiByZWR1Y2UpIHsg'
    'LnN4LWRvdCB7IGFuaW1hdGlvbjogbm9uZTsgfSAuc3gtYmFyLWZpbGwgeyB0cmFuc2l0aW9uOiBu'
    'b25lOyB9IH0KICAgICAgYH08L3N0eWxlPgogICAgPC9kaXY+CiAgKTsKfQoKZnVuY3Rpb24gS3Bp'
    'KHsgaWNvbiwgbGFiZWwsIHZhbHVlLCB0b25lLCBsaXZlIH06IHsgaWNvbjogUmVhY3QuUmVhY3RO'
    'b2RlOyBsYWJlbDogc3RyaW5nOyB2YWx1ZTogc3RyaW5nOyB0b25lPzogJ29rJyB8ICd3YXJuJzsg'
    'bGl2ZT86IGJvb2xlYW4gfSkgewogIGNvbnN0IGNvbG9yID0gdG9uZSA9PT0gJ3dhcm4nID8gJ3Zh'
    'cigtLWFtYmVyLCAjQzI1QTFBKScgOiAndmFyKC0taW5rLCAjMEQxQTBGKSc7CiAgcmV0dXJuICgK'
    'ICAgIDxkaXYgc3R5bGU9e3sgZGlzcGxheTogJ2ZsZXgnLCBhbGlnbkl0ZW1zOiAnY2VudGVyJywg'
    'Z2FwOiA5IH19PgogICAgICA8c3BhbiBzdHlsZT17eyBjb2xvcjogdG9uZSA9PT0gJ3dhcm4nID8g'
    'J3ZhcigtLWFtYmVyLCAjQzI1QTFBKScgOiAndmFyKC0tZ3JlZW4tc29mdCwgIzRBN0M1OSknLCBk'
    'aXNwbGF5OiAnZmxleCcgfX0+e2ljb259PC9zcGFuPgogICAgICA8ZGl2PgogICAgICAgIDxkaXYg'
    'c3R5bGU9e3sgZm9udFNpemU6IDkuNSwgZm9udFdlaWdodDogNTAwLCBsZXR0ZXJTcGFjaW5nOiAn'
    'MC4xMmVtJywgdGV4dFRyYW5zZm9ybTogJ3VwcGVyY2FzZScsIGNvbG9yOiAndmFyKC0taW5rLWZh'
    'aW50LCByZ2JhKDEzLDI2LDE1LDAuNCkpJyB9fT57bGFiZWx9PC9kaXY+CiAgICAgICAgPGRpdiBz'
    'dHlsZT17eyBmb250U2l6ZTogJ2NsYW1wKDE1cHgsMS42dncsMjJweCknLCBmb250V2VpZ2h0OiA2'
    'MDAsIGxldHRlclNwYWNpbmc6ICctMC4wMmVtJywgY29sb3IsIGZvbnRWYXJpYW50TnVtZXJpYzog'
    'J3RhYnVsYXItbnVtcycsIGRpc3BsYXk6ICdmbGV4JywgYWxpZ25JdGVtczogJ2NlbnRlcicsIGdh'
    'cDogNiB9fT4KICAgICAgICAgIHt2YWx1ZX0KICAgICAgICAgIHtsaXZlICYmIDxzcGFuIHN0eWxl'
    'PXt7IHdpZHRoOiA2LCBoZWlnaHQ6IDYsIGJvcmRlclJhZGl1czogJzUwJScsIGJhY2tncm91bmQ6'
    'ICd2YXIoLS1ncmVlbi1zb2Z0LCAjNEE3QzU5KScsIGFuaW1hdGlvbjogJ3N4LXB1bHNlIDEuOHMg'
    'ZWFzZS1pbi1vdXQgaW5maW5pdGUnIH19IC8+fQogICAgICAgIDwvZGl2PgogICAgICA8L2Rpdj4K'
    'ICAgIDwvZGl2PgogICk7Cn0KCmZ1bmN0aW9uIE1ldHJpYyh7IGxhYmVsLCB2YWx1ZSwgdG9uZSB9'
    'OiB7IGxhYmVsOiBzdHJpbmc7IHZhbHVlOiBzdHJpbmc7IHRvbmU/OiAnd2FybicgfSkgewogIHJl'
    'dHVybiAoCiAgICA8ZGl2IHN0eWxlPXt7IGRpc3BsYXk6ICdmbGV4JywgZmxleERpcmVjdGlvbjog'
    'J2NvbHVtbicsIGdhcDogMSwgbWluV2lkdGg6IDAgfX0+CiAgICAgIDxzcGFuIHN0eWxlPXt7IGZv'
    'bnRTaXplOiA5LCBmb250V2VpZ2h0OiA1MDAsIGxldHRlclNwYWNpbmc6ICcwLjA4ZW0nLCB0ZXh0'
    'VHJhbnNmb3JtOiAndXBwZXJjYXNlJywgY29sb3I6ICd2YXIoLS1pbmstZmFpbnQsIHJnYmEoMTMs'
    'MjYsMTUsMC4zOCkpJyB9fT57bGFiZWx9PC9zcGFuPgogICAgICA8c3BhbiBzdHlsZT17eyBmb250'
    'U2l6ZTogJ2NsYW1wKDEycHgsMS4ydncsMTVweCknLCBmb250V2VpZ2h0OiA2MDAsIGxldHRlclNw'
    'YWNpbmc6ICctMC4wMWVtJywgY29sb3I6IHRvbmUgPT09ICd3YXJuJyA/ICd2YXIoLS1hbWJlciwg'
    'I0MyNUExQSknIDogJ3ZhcigtLWluaywgIzBEMUEwRiknLCBmb250VmFyaWFudE51bWVyaWM6ICd0'
    'YWJ1bGFyLW51bXMnLCB3aGl0ZVNwYWNlOiAnbm93cmFwJywgb3ZlcmZsb3c6ICdoaWRkZW4nLCB0'
    'ZXh0T3ZlcmZsb3c6ICdlbGxpcHNpcycgfX0+e3ZhbHVlfTwvc3Bhbj4KICAgIDwvZGl2PgogICk7'
    'Cn0K'
)

GATE_B64 = (
    'J3VzZSBjbGllbnQnOwoKaW1wb3J0IHsgdXNlRWZmZWN0LCB1c2VTdGF0ZSB9IGZyb20gJ3JlYWN0'
    'JzsKaW1wb3J0IHsgTG9jayB9IGZyb20gJ2x1Y2lkZS1yZWFjdCc7CmltcG9ydCBQaXBlbGluZXND'
    'b250ZW50IGZyb20gJy4vX2NvbnRlbnQnOwoKY29uc3QgQURNSU5fS0VZID0gJ3BsYW50YS1vcHMn'
    'Owpjb25zdCBTVE9SRV9LRVkgPSAncGxhbnRhLWFkbWluLWtleSc7CgpleHBvcnQgZGVmYXVsdCBm'
    'dW5jdGlvbiBQaXBlbGluZXNQYWdlKCkgewogIGNvbnN0IFthdXRoZWQsIHNldEF1dGhlZF0gPSB1'
    'c2VTdGF0ZShmYWxzZSk7CiAgY29uc3QgW3JlYWR5LCBzZXRSZWFkeV0gPSB1c2VTdGF0ZShmYWxz'
    'ZSk7CiAgY29uc3QgW3ZhbCwgc2V0VmFsXSA9IHVzZVN0YXRlKCcnKTsKCiAgdXNlRWZmZWN0KCgp'
    'ID0+IHsKICAgIHRyeSB7CiAgICAgIGNvbnN0IHVybCA9IG5ldyBVUkxTZWFyY2hQYXJhbXMod2lu'
    'ZG93LmxvY2F0aW9uLnNlYXJjaCk7CiAgICAgIGNvbnN0IGZyb21VcmwgPSB1cmwuZ2V0KCdrZXkn'
    'KTsKICAgICAgY29uc3Qgc3RvcmVkID0gbG9jYWxTdG9yYWdlLmdldEl0ZW0oU1RPUkVfS0VZKTsK'
    'ICAgICAgaWYgKGZyb21VcmwgPT09IEFETUlOX0tFWSB8fCBzdG9yZWQgPT09IEFETUlOX0tFWSkg'
    'ewogICAgICAgIGlmIChmcm9tVXJsID09PSBBRE1JTl9LRVkpIGxvY2FsU3RvcmFnZS5zZXRJdGVt'
    'KFNUT1JFX0tFWSwgQURNSU5fS0VZKTsKICAgICAgICBzZXRBdXRoZWQodHJ1ZSk7CiAgICAgIH0K'
    'ICAgIH0gY2F0Y2gge30KICAgIHNldFJlYWR5KHRydWUpOwogIH0sIFtdKTsKCiAgY29uc3QgdHJ5'
    'S2V5ID0gKCkgPT4gewogICAgaWYgKHZhbC50cmltKCkgPT09IEFETUlOX0tFWSkgewogICAgICB0'
    'cnkgeyBsb2NhbFN0b3JhZ2Uuc2V0SXRlbShTVE9SRV9LRVksIEFETUlOX0tFWSk7IH0gY2F0Y2gg'
    'e30KICAgICAgc2V0QXV0aGVkKHRydWUpOwogICAgfSBlbHNlIHsKICAgICAgYWxlcnQoJ0NoYXZl'
    'IGluY29ycmVjdGEuJyk7CiAgICB9CiAgfTsKCiAgaWYgKCFyZWFkeSkgcmV0dXJuIG51bGw7CiAg'
    'aWYgKGF1dGhlZCkgcmV0dXJuIDxQaXBlbGluZXNDb250ZW50IC8+OwoKICByZXR1cm4gKAogICAg'
    'PGRpdiBzdHlsZT17ewogICAgICBwb3NpdGlvbjogJ2ZpeGVkJywgdG9wOiAndmFyKC0tdG9wYmFy'
    'LWgsIDcycHgpJywgbGVmdDogMCwgcmlnaHQ6IDAsIGJvdHRvbTogMCwKICAgICAgZGlzcGxheTog'
    'J2ZsZXgnLCBmbGV4RGlyZWN0aW9uOiAnY29sdW1uJywgYWxpZ25JdGVtczogJ2NlbnRlcicsIGp1'
    'c3RpZnlDb250ZW50OiAnY2VudGVyJywKICAgICAgZ2FwOiAxOCwgYmFja2dyb3VuZDogJ3Zhcigt'
    'LXBhcGVyLCAjRkFGQUY3KScsIGNvbG9yOiAndmFyKC0taW5rLCAjMEQxQTBGKScsIHBhZGRpbmc6'
    'IDI0LAogICAgfX0+CiAgICAgIDxMb2NrIHNpemU9ezI4fSBzdHJva2VXaWR0aD17MS40fSBzdHls'
    'ZT17eyBjb2xvcjogJ3ZhcigtLWdyZWVuLXNvZnQsICM0QTdDNTkpJyB9fSAvPgogICAgICA8ZGl2'
    'IHN0eWxlPXt7IHRleHRBbGlnbjogJ2NlbnRlcicgfX0+CiAgICAgICAgPGgxIHN0eWxlPXt7IGZv'
    'bnRTaXplOiAnY2xhbXAoMjBweCwyLjZ2dywzMHB4KScsIGZvbnRXZWlnaHQ6IDMwMCwgbGV0dGVy'
    'U3BhY2luZzogJy0wLjAzZW0nLCBtYXJnaW46IDAgfX0+QWNlc3NvIHJlc3RyaXRvPC9oMT4KICAg'
    'ICAgICA8cCBzdHlsZT17eyBmb250U2l6ZTogMTQsIGNvbG9yOiAndmFyKC0taW5rLXNvZnQsIHJn'
    'YmEoMTMsMjYsMTUsMC41NSkpJywgbWFyZ2luVG9wOiA2LCBmb250U3R5bGU6ICdpdGFsaWMnIH19'
    'Pk9wZXJhdGlvbnMgb25seTwvcD4KICAgICAgPC9kaXY+CiAgICAgIDxkaXYgc3R5bGU9e3sgZGlz'
    'cGxheTogJ2ZsZXgnLCBnYXA6IDgsIHdpZHRoOiAnbWluKDM2MHB4LCA5MHZ3KScgfX0+CiAgICAg'
    'ICAgPGlucHV0CiAgICAgICAgICB0eXBlPSJwYXNzd29yZCIKICAgICAgICAgIHZhbHVlPXt2YWx9'
    'CiAgICAgICAgICBvbkNoYW5nZT17KGUpID0+IHNldFZhbChlLnRhcmdldC52YWx1ZSl9CiAgICAg'
    'ICAgICBvbktleURvd249eyhlKSA9PiB7IGlmIChlLmtleSA9PT0gJ0VudGVyJykgdHJ5S2V5KCk7'
    'IH19CiAgICAgICAgICBwbGFjZWhvbGRlcj0iQ2hhdmUgZGUgYWNlc3NvIgogICAgICAgICAgc3R5'
    'bGU9e3sgZmxleDogMSwgcGFkZGluZzogJzEycHggMTZweCcsIGJvcmRlclJhZGl1czogOTk5LCBi'
    'b3JkZXI6ICcxcHggc29saWQgdmFyKC0tZ3JlZW4sICMxQjNBMjEpJywgZm9udFNpemU6IDE1LCBv'
    'dXRsaW5lOiAnbm9uZScsIGZvbnRGYW1pbHk6ICdpbmhlcml0JywgYmFja2dyb3VuZDogJyNmZmYn'
    'LCBjb2xvcjogJ3ZhcigtLWluaywgIzBEMUEwRiknIH19CiAgICAgICAgLz4KICAgICAgICA8YnV0'
    'dG9uIG9uQ2xpY2s9e3RyeUtleX0gc3R5bGU9e3sgYmFja2dyb3VuZDogJ3ZhcigtLWdyZWVuLCAj'
    'MUIzQTIxKScsIGNvbG9yOiAnI2ZmZicsIGJvcmRlcjogJ25vbmUnLCBib3JkZXJSYWRpdXM6IDk5'
    'OSwgcGFkZGluZzogJzEycHggMjJweCcsIGZvbnRTaXplOiAxNCwgZm9udFdlaWdodDogNjAwLCBj'
    'dXJzb3I6ICdwb2ludGVyJywgZm9udEZhbWlseTogJ2luaGVyaXQnIH19PkVudHJhcjwvYnV0dG9u'
    'PgogICAgICA8L2Rpdj4KICAgICAgPGEgaHJlZj0iL3YyIiBzdHlsZT17eyBmb250U2l6ZTogMTMs'
    'IGNvbG9yOiAndmFyKC0tZ3JlZW4tc29mdCwgIzRBN0M1OSknLCB0ZXh0RGVjb3JhdGlvbjogJ25v'
    'bmUnIH19PuKGkCBWb2x0YXIgYW8gaW7DrWNpbzwvYT4KICAgIDwvZGl2PgogICk7Cn0K'
)


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0


def main():
    root = Path.cwd()
    if not (root / "frontend").exists():
        print("ERRO: corre a partir de ~/planta_rock4"); sys.exit(1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── 1. SENSORS ──────────────────────────────────────────────
    print("=" * 64); print("  1. /v2/sensors — 100% sem scroll, wow"); print("=" * 64)
    sx = root / "frontend" / "app" / "v2" / "sensors" / "page.tsx"
    sx.parent.mkdir(parents=True, exist_ok=True)
    if sx.exists(): shutil.copy2(sx, sx.with_suffix(f".tsx.bak.v32.{stamp}"))
    sx.write_bytes(base64.b64decode("".join(SENSORS_B64)))
    print(f"  OK frontend/app/v2/sensors/page.tsx")

    # ── 2. PIPELINES admin gate ─────────────────────────────────
    print(); print("=" * 64); print("  2. /v2/pipelines — so admin (?key=planta-ops)"); print("=" * 64)
    pdir = root / "frontend" / "app" / "v2" / "pipelines"
    ppage = pdir / "page.tsx"
    pcontent = pdir / "_content.tsx"
    if not pdir.exists():
        print("  i /v2/pipelines nao existe — crio so o gate (sem conteudo).")
        pdir.mkdir(parents=True, exist_ok=True)
        # _content placeholder
        pcontent.write_text(
            "'use client';\nexport default function PipelinesContent() {\n"
            "  return <div style={{padding:40}}>Pipelines (admin).</div>;\n}\n"
        )
        print("  OK _content.tsx placeholder criado")
    else:
        if pcontent.exists():
            print("  i _content.tsx ja existe — nao sobreponho.")
        else:
            cur = ppage.read_text()
            shutil.copy2(ppage, ppage.with_suffix(f".tsx.bak.v32.{stamp}"))
            # mover o conteudo actual para _content.tsx, renomeando o default export
            moved = cur
            moved = re.sub(r"export default function \w+", "export default function PipelinesContent", moved, count=1)
            if "export default function PipelinesContent" not in moved:
                # caso seja "export default function() {" ou arrow
                moved = re.sub(r"export default function\s*\(", "export default function PipelinesContent(", moved, count=1)
            if "export default function PipelinesContent" not in moved:
                print("  ! Nao consegui renomear o export default do pipelines.")
                print("    Verifica manualmente: o gate importa um default de ./_content")
            pcontent.write_text(moved)
            print(f"  OK conteudo actual movido -> _content.tsx ({len(moved)} B)")

    # escrever o gate como page.tsx
    if ppage.exists() and not ppage.with_suffix(f".tsx.bak.v32.{stamp}").exists():
        shutil.copy2(ppage, ppage.with_suffix(f".tsx.bak.v32.gate.{stamp}"))
    ppage.write_bytes(base64.b64decode("".join(GATE_B64)))
    print(f"  OK frontend/app/v2/pipelines/page.tsx = gate de admin")

    # ── 3. TopBar: remover Pipelines do nav ─────────────────────
    print(); print("=" * 64); print("  3. TopBar — remover 'Pipelines' do menu"); print("=" * 64)
    tb = root / "frontend" / "components" / "v2" / "TopBar.tsx"
    if tb.exists():
        c = tb.read_text()
        line_rx = re.compile(r"\n\s*\{\s*href:\s*'/v2/pipelines'[^}]*\},?")
        if line_rx.search(c):
            shutil.copy2(tb, tb.with_suffix(f".tsx.bak.v32.{stamp}"))
            c = line_rx.sub("", c, count=1)
            tb.write_text(c)
            print("  OK item 'Pipelines' removido do nav (pagina continua acessivel por URL+chave)")
        else:
            print("  i Nao encontrei o item Pipelines no nav (ja removido?).")
    else:
        print("  i TopBar.tsx nao encontrado.")

    # ── commit ──────────────────────────────────────────────────
    print(); print("=" * 64); print("  GIT"); print("=" * 64)
    run("git add frontend/app/v2/sensors/page.tsx frontend/app/v2/pipelines/ frontend/components/v2/TopBar.tsx", cwd=str(root))
    run('git commit -m "feat(v32): sensors 100vh wow + pipelines admin-gate + nav sem Pipelines"', cwd=str(root))
    run("git push", cwd=str(root))

    print()
    print("  Aguarda ~90s e CMD+SHIFT+R:")
    print("   - /v2/sensors  -> grelha dos 8 clusters, 100% ecra, sem scroll.")
    print("   - /v2/pipelines -> pede chave. Acesso: /v2/pipelines?key=planta-ops")
    print("   - O 'Pipelines' deixou de aparecer no menu de topo.")
    print()
    print("  (muda a chave 'planta-ops' editando ADMIN_KEY no page.tsx do pipelines)")


if __name__ == "__main__":
    main()

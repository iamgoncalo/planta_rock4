'use client';

import { useLiveV3 } from './LiveContextV3';
import TopBarV3 from './TopBarV3';

export default function TopBarV3Wrapper() {
  const { connected } = useLiveV3();
  return <TopBarV3 connected={connected} />;
}

import type { ClusterId, ClusterState } from './mural-types';

type BilingualPhrase = [string, string]; // [pt-PT, en]

interface ClusterCopy {
  calmo: BilingualPhrase[];
  activo: BilingualPhrase[];
  intenso: BilingualPhrase[];
}

export const CLUSTER_COPY: Record<ClusterId, ClusterCopy> = {
  '01': {
    calmo: [
      [
        'Bebedouro EPAL aqui. Hidrata, esvazia, repete.',
        'EPAL fountain here. Drink, drain, repeat.',
      ],
      [
        'Norte. Sem multidão. Sem mistério.',
        'North side. No crowd. No mystery.',
      ],
      [
        'A entrada fica a passos. E a saída também.',
        'The gate is steps away. So is the exit.',
      ],
    ],
    activo: [
      [
        'Chegada constante. Saída constante.',
        'Steady in. Steady out.',
      ],
      [
        'Ritmo de entrada. Espera de café.',
        'Arrival pace. Coffee-break wait.',
      ],
      [
        'Norte em movimento. Faz fila curta.',
        'North in motion. Short queue.',
      ],
    ],
    intenso: [
      [
        'Cheio à entrada. WC-07 nos lockers é mais discreto.',
        'Busy at the gate. WC-07 by the lockers is quieter.',
      ],
      [
        'Pressão máxima no norte. Encosta a dois minutos, mais fácil.',
        'Peak pressure up north. The slope is two minutes away, calmer.',
      ],
      [
        'Pico na entrada norte. WC-03 a 33 m do portão principal respira.',
        'North gate packed. Main gate cluster, 33 m in, has room.',
      ],
    ],
  },

  '02': {
    calmo: [
      [
        'Atrás do palco, à frente da multidão.',
        'Backstage feel, front-row access.',
      ],
      [
        'O VIP é não esperar.',
        'The real VIP is no queue.',
      ],
      [
        'Super Bock ao lado. Prioridades certas.',
        'Super Bock stage next door. Priorities right.',
      ],
    ],
    activo: [
      [
        'Pausa entre dois solos.',
        'A pause between two solos.',
      ],
      [
        'Zona VIP. Espera de intervalo.',
        'VIP zone. Interval wait.',
      ],
      [
        'Super Bock a tocar. Filas a rodar.',
        'Super Bock sounds. Queues turning.',
      ],
    ],
    intenso: [
      [
        'Cheio aqui. WC-04 lá em cima tem vista grátis.',
        'Full here. WC-04 up the hill comes with a free view.',
      ],
      [
        'VIP esgotado. WC-06 perto do palco Bacana Play tem mais espaço.',
        'VIP at capacity. WC-06 near Bacana Play stage has room.',
      ],
      [
        'Pico no Super Bock. WC-03 à entrada tem menos pressão.',
        'Super Bock peak. Main gate WC has less pressure.',
      ],
    ],
  },

  '03': {
    calmo: [
      [
        'Trinta segundos do portão. Logística, resolvida.',
        'Thirty seconds from the gate. Logistics, solved.',
      ],
      [
        'O mais perto da entrada está livre.',
        'The one closest to the gate is open.',
      ],
      [
        'Ninguém sabe que estás aqui. Fica o segredo.',
        'Nobody knows you are here. Keep it that way.',
      ],
    ],
    activo: [
      [
        'Fila gentil. A entrada também.',
        'Gentle queue. Gentle entrance.',
      ],
      [
        'Perto de tudo. Incluindo da fila.',
        'Close to everything. Including the queue.',
      ],
      [
        'Entrada. Movimento. Fluxo normal.',
        'Entry point. Movement. Normal flow.',
      ],
    ],
    intenso: [
      [
        'Lotado à porta. WC-05 fica ao lado, encosta acima.',
        'Packed at the door. WC-05 is next door, up the slope.',
      ],
      [
        'Portal congestionado. WC-07 nos lockers tem menos trânsito.',
        'Portal congested. Locker WC has less traffic.',
      ],
      [
        'Entrada a rebentar. WC-06 junto ao palco maior está disponível.',
        'Gate overloaded. WC-06 by the big stage has space.',
      ],
    ],
  },

  '04': {
    calmo: [
      [
        'Uma vista. Uma casa de banho. Ambas com o Tejo.',
        'A view. A loo. Both featuring the Tagus.',
      ],
      [
        'Subiste por mim. Obrigada.',
        'You climbed for me. Thank you.',
      ],
      [
        'Vista do Parque Tejo. Sem fila. Que mais se quer?',
        'Parque Tejo view. No queue. What more could you ask?',
      ],
    ],
    activo: [
      [
        'A subida pede tempo. A descida recompensa-o.',
        'The climb takes time. The descent gives it back.',
      ],
      [
        'Vista panorâmica, espera breve.',
        'Panoramic view, brief wait.',
      ],
      [
        'Cá em cima o ritmo é mais calmo.',
        'Up here the pace is gentler.',
      ],
    ],
    intenso: [
      [
        'Topo lotado. WC-02 mora aqui em baixo, perto do Super Bock.',
        'Summit is full. WC-02 lives just below, near Super Bock.',
      ],
      [
        'Vista partilhada demais. WC-08 no sul tem sossego.',
        'Too popular a view. WC-08 in the south has quiet.',
      ],
      [
        'Lá cima a transbordar. Encosta a dois minutos tem menos gente.',
        'Overflowing at the top. Slope is two minutes with fewer people.',
      ],
    ],
  },

  '05': {
    calmo: [
      [
        'Unissex. A regra de género perdeu-se na entrada.',
        'All genders. The gender rule got lost at the gate.',
      ],
      [
        'Primeiro a chegar, primeiro a sair.',
        'First in, first out.',
      ],
      [
        'Encosta serena. Trinta metros da entrada principal.',
        'Gentle slope. Thirty metres from the main gate.',
      ],
    ],
    activo: [
      [
        'Meio-tempo. Tempo certo para a fila andar.',
        'Half-time. Right time for the queue to move.',
      ],
      [
        'Trinta metros da porta principal. Vale a ida.',
        'Thirty metres from the main door. Worth the walk.',
      ],
      [
        'Movimento normal. Sem drama.',
        'Normal flow. No drama.',
      ],
    ],
    intenso: [
      [
        'Sobrelotado. WC-03 está literalmente ao lado, à entrada principal.',
        'Overloaded. WC-03 is literally next door, at the main gate.',
      ],
      [
        'Encosta cheia. WC-06 junto ao palco Bacana Play tem mais espaço.',
        'Slope is full. WC-06 by Bacana Play stage has more room.',
      ],
      [
        'Cheio aqui. WC-07 nos lockers é uma boa alternativa.',
        'Full here. WC-07 by the lockers is a solid alternative.',
      ],
    ],
  },

  '06': {
    calmo: [
      [
        'Quarenta cabines. Zero filas. Tu fazes as contas.',
        'Forty stalls. Zero queues. You do the math.',
      ],
      [
        'O maior do festival, hoje à tua espera.',
        'The biggest one, waiting for you today.',
      ],
      [
        'Bacana Play a tocar. Fila a não fazer.',
        'Bacana Play playing. No queue forming.',
      ],
    ],
    activo: [
      [
        'É grande. Mexe-se grande. Tu também.',
        'It is big. It moves big. So will you.',
      ],
      [
        'Palco cheio, casas de banho a acompanhar.',
        'Stage full, facilities following suit.',
      ],
      [
        'O maior tem o seu ritmo.',
        'The biggest has its rhythm.',
      ],
    ],
    intenso: [
      [
        'Até quarenta cabines têm limite. WC-07 nos lockers está livre.',
        'Even forty stalls have a limit. WC-07 by the lockers is open.',
      ],
      [
        'Bacana Play em pico. WC-05 na encosta respira melhor.',
        'Bacana Play at peak. Slope WC breathes easier.',
      ],
      [
        'Lotado junto ao Bacana. WC-08 no sul tem sossego garantido.',
        'Packed near Bacana. South WC has guaranteed quiet.',
      ],
    ],
  },

  '07': {
    calmo: [
      [
        'Lockers ao lado. Casa de banho de bónus.',
        'Lockers next door. Loo as a bonus.',
      ],
      [
        'Antes do Welcome Wall, antes da fila.',
        'Before the Welcome Wall, before the crowd.',
      ],
      [
        'Discreto. Eficiente. Perto dos lockers.',
        'Discreet. Efficient. Close to the lockers.',
      ],
    ],
    activo: [
      [
        'Cruzamento triplo. Funciona como deve.',
        'Triple junction. Working as designed.',
      ],
      [
        'Zona dos lockers. Fluxo constante.',
        'Locker zone. Steady flow.',
      ],
      [
        'Welcome Wall a dez metros. Espera curta.',
        'Welcome Wall ten metres back. Short wait.',
      ],
    ],
    intenso: [
      [
        'Triplo cheio. WC-08 fica longe da multidão, sul do recinto.',
        'Triple packed. WC-08 lives far from the crowd, south side.',
      ],
      [
        'Welcome Wall congestionada. WC-04 lá em cima tem vista e espaço.',
        'Welcome Wall congested. WC-04 uphill has views and space.',
      ],
      [
        'Cheio nos lockers. WC-05 na encosta está a cinco minutos.',
        'Full by the lockers. Slope cluster is five minutes away.',
      ],
    ],
  },

  '08': {
    calmo: [
      [
        'Anda-se um pouco. Não se espera nada.',
        'Short walk. No wait at the end.',
      ],
      [
        'Aqui ainda se ouve a brisa.',
        'You can still hear the breeze here.',
      ],
      [
        'Sul. Tranquilo por natureza.',
        'South. Quiet by nature.',
      ],
    ],
    activo: [
      [
        'A caminhada vale o tempo que poupa.',
        'The walk pays for itself in time saved.',
      ],
      [
        'O sul também tem as suas horas.',
        'The south has its moments too.',
      ],
      [
        'Exterior. Espera moderada.',
        'Outdoor. Moderate wait.',
      ],
    ],
    intenso: [
      [
        'Até aqui chegou cheio. WC-06 é o gigante junto ao palco Bacana Play.',
        'Even here is full. WC-06 is the giant one by Bacana Play stage.',
      ],
      [
        'Sul a encher. WC-07 nos lockers está mais livre.',
        'South filling up. Locker cluster has more room.',
      ],
      [
        'Brisa e fila. WC-04 lá em cima garante espaço e panorama.',
        'Breeze and queue. WC-04 uphill offers space and a view.',
      ],
    ],
  },
};

export const CLUSTER_META: Record<
  ClusterId,
  {
    labelPt: string;
    genderLabel: string;
    landmarkPt: string;
    landmarkEn: string;
    ax: string;
    ay: string;
  }
> = {
  '01': {
    labelPt: 'WC-01',
    genderLabel: 'M / F',
    landmarkPt: 'Entrada Norte · Bebedouro EPAL',
    landmarkEn: 'North Gate · EPAL Fountain',
    ax: '25%',
    ay: '35%',
  },
  '02': {
    labelPt: 'WC-02',
    genderLabel: 'M / F',
    landmarkPt: 'Palco Super Bock · zona VIP',
    landmarkEn: 'Super Bock Stage · VIP zone',
    ax: '70%',
    ay: '30%',
  },
  '03': {
    labelPt: 'WC-03',
    genderLabel: 'M / F',
    landmarkPt: 'Entrada Principal · 33 m do portão',
    landmarkEn: 'Main Gate · 33 m from entrance',
    ax: '40%',
    ay: '60%',
  },
  '04': {
    labelPt: 'WC-04',
    genderLabel: 'M / F',
    landmarkPt: 'Topo · vista sobre o Parque Tejo',
    landmarkEn: 'Hilltop · Parque Tejo view',
    ax: '30%',
    ay: '70%',
  },
  '05': {
    labelPt: 'WC-05',
    genderLabel: '●',
    landmarkPt: 'Encosta · entrada principal a 30 m',
    landmarkEn: 'Slope · 30 m from Main Gate',
    ax: '80%',
    ay: '25%',
  },
  '06': {
    labelPt: 'WC-06',
    genderLabel: '●',
    landmarkPt: 'Palco Bacana Play · o maior do festival',
    landmarkEn: 'Bacana Play Stage · the biggest one',
    ax: '20%',
    ay: '55%',
  },
  '07': {
    labelPt: 'WC-07',
    genderLabel: 'M / F',
    landmarkPt: 'Lockers · Welcome Wall a 10 m',
    landmarkEn: 'Lockers · Welcome Wall 10 m away',
    ax: '65%',
    ay: '40%',
  },
  '08': {
    labelPt: 'WC-08',
    genderLabel: 'M / F',
    landmarkPt: 'Sul · zona exterior · longe da multidão',
    landmarkEn: 'South · outdoor zone · far from the crowd',
    ax: '50%',
    ay: '60%',
  },
};

export function getPhrase(
  id: ClusterId,
  state: ClusterState,
  idx: number,
): [string, string] {
  const pool = CLUSTER_COPY[id][state];
  return pool[idx % pool.length];
}

export function poolLength(id: ClusterId, state: ClusterState): number {
  return CLUSTER_COPY[id][state].length;
}

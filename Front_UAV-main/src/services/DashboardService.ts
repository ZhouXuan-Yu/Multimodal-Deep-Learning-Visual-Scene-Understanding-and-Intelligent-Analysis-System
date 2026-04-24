/**
 * 文件名: DashboardService.ts
 * 描述: 数据持久化与导入服务
 * 作用:
 * - 为数据分析大屏提供持久化存储（localStorage）
 * - 管理智眸千析、智程导航、联系我们三模块的数据写入
 * - 支持各模块操作后自动导入数据到大屏
 * - 提供模拟数据生成（演示用）
 */

// ============================================================
//  Types
// ============================================================

export interface PersonRecord {
  id: string;
  timestamp: number;
  gender: '男' | '女' | '未知';
  age: string;
  upperColor: string;
  lowerColor: string;
  confidence: number;
  processingTime: number;
  imageUrl?: string;
}

export interface RouteRecord {
  id: string;
  timestamp: number;
  startPoint: string;
  endPoint: string;
  waypoints: string[];
  cities: string;
  strategy: 'fastest' | 'economic' | 'shortest';
  duration: number;
  distance: string;
  toll: number;
  hasRestriction: boolean;
}

export interface ConsultationRecord {
  id: string;
  timestamp: number;
  name: string;
  email: string;
  interest: string;
  interestLabel: string;
  message: string;
  status: 'sent' | 'processing' | 'failed';
  processingTime?: number;
  aiReply?: string;   // AI分析后的回复内容
  userQuestion?: string; // 用户原始问题（message的别名，方便展示）
}

export interface DroneTelemetryRecord {
  id: string;
  timestamp: number;
  battery: number;
  signal: number;
  speed: number;
  altitude: number;
  status: string;
}

// ============================================================
//  Constants
// ============================================================

const KEYS = {
  PERSON_RECORDS:    'dashboard_person_records',
  ROUTE_RECORDS:    'dashboard_route_records',
  CONSULTATION:      'dashboard_consultation_records',
  DRONE_SNAPSHOTS:  'dashboard_drone_snapshots',
  INITIALIZED:       'dashboard_initialized',
} as const;

const MAX_RECORDS = 200;

// ============================================================
//  Generic helpers
// ============================================================

function loadFromStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function saveToStorage<T>(key: string, data: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.error('[DashboardService] saveToStorage failed:', e);
  }
}

function trimRecords<T extends { timestamp: number }>(records: T[]): T[] {
  if (records.length > MAX_RECORDS) {
    return records.slice(-MAX_RECORDS);
  }
  return records;
}

// ============================================================
//  Simulation data generators
// ============================================================

const GENDERS: PersonRecord['gender'][] = ['男', '女', '未知'];
const GENDER_WEIGHTS = [0.55, 0.40, 0.05];
const COLORS = ['黑色', '白色', '蓝色', '红色', '灰色', '绿色', '黄色', '紫色', '棕色', '粉色'];
const COLOR_WEIGHTS = [0.18, 0.15, 0.14, 0.10, 0.12, 0.08, 0.07, 0.06, 0.05, 0.05];
const AGE_RANGES = ['3-12', '13-17', '18-25', '26-35', '36-45', '46-55', '56-65', '65+'];
const AGE_WEIGHTS = [0.05, 0.08, 0.25, 0.28, 0.18, 0.10, 0.04, 0.02];

const CITIES = ['北京', '上海', '深圳', '广州', '成都', '杭州', '武汉', '西安', '重庆', '南京', '天津', '苏州', '长沙', '郑州', '东莞'];
const STRATEGIES: RouteRecord['strategy'][] = ['fastest', 'economic', 'shortest'];
const STRATEGY_LABELS: Record<RouteRecord['strategy'], string> = {
  fastest: '最快路线',
  economic: '最经济路线',
  shortest: '最短距离',
};

const INTERESTS = [
  { value: 'path-planning', label: '路径规划' },
  { value: 'person-recognition', label: '人员识别' },
  { value: 'vehicle-monitoring', label: '车辆监控' },
  { value: 'data-dashboard', label: '数据仪表盘' },
  { value: 'general', label: '一般咨询' },
];

function weightedRandom<T>(items: T[], weights: number[]): T {
  const r = Math.random();
  let cumulative = 0;
  for (let i = 0; i < items.length; i++) {
    cumulative += weights[i];
    if (r < cumulative) return items[i];
  }
  return items[items.length - 1];
}

function randBetween(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function randInt(min: number, max: number) {
  return Math.floor(randBetween(min, max + 1));
}

function generatePersonRecord(timestamp?: number): PersonRecord {
  const gender = weightedRandom(GENDERS, GENDER_WEIGHTS);
  const ageRange = weightedRandom(AGE_RANGES, AGE_WEIGHTS);
  const [ageMin, ageMax] = ageRange.split('-').map(v => v === '65+' ? 65 : parseInt(v));
  const age = `${ageMin}-${ageMax}`;
  return {
    id: `person-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp: timestamp ?? Date.now() - randBetween(0, 7 * 24 * 3600 * 1000),
    gender,
    age,
    upperColor: weightedRandom(COLORS, COLOR_WEIGHTS),
    lowerColor: weightedRandom(COLORS, COLOR_WEIGHTS),
    confidence: parseFloat((randBetween(0.65, 0.99)).toFixed(3)),
    processingTime: parseFloat(randBetween(0.8, 2.5).toFixed(2)),
  };
}

function generateRouteRecord(timestamp?: number): RouteRecord {
  const startCity = CITIES[randInt(0, CITIES.length - 1)];
  let endCity = CITIES[randInt(0, CITIES.length - 1)];
  while (endCity === startCity) endCity = CITIES[randInt(0, CITIES.length - 1)];
  const waypointCount = Math.random() > 0.6 ? randInt(1, 3) : 0;
  const waypoints: string[] = [];
  for (let i = 0; i < waypointCount; i++) {
    const via = CITIES[randInt(0, CITIES.length - 1)];
    if (![startCity, endCity, ...waypoints].includes(via)) waypoints.push(via);
  }
  const distance = (randBetween(50, 800)).toFixed(1);
  const duration = Math.round(randBetween(40, 600));
  return {
    id: `route-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp: timestamp ?? Date.now() - randBetween(0, 30 * 24 * 3600 * 1000),
    startPoint: startCity,
    endPoint: endCity,
    waypoints,
    cities: waypoints.length > 0 ? [startCity, ...waypoints, endCity].join(' → ') : `${startCity} → ${endCity}`,
    strategy: STRATEGIES[randInt(0, 2)],
    duration,
    distance,
    toll: Math.round(randBetween(0, 200)),
    hasRestriction: Math.random() > 0.85,
  };
}

function generateConsultationRecord(timestamp?: number): ConsultationRecord {
  const interest = INTERESTS[randInt(0, INTERESTS.length - 1)];
  const statuses: ConsultationRecord['status'][] = ['sent', 'sent', 'sent', 'sent', 'processing', 'failed'];
  return {
    id: `consult-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp: timestamp ?? Date.now() - randBetween(0, 30 * 24 * 3600 * 1000),
    name: ['王先生', '李女士', '张同学', '刘经理', '陈工程师'][randInt(0, 4)],
    email: `user${randInt(1, 999)}@example.com`,
    interest: interest.value,
    interestLabel: interest.label,
    message: '关于系统功能的详细咨询...',
    status: statuses[randInt(0, statuses.length - 1)],
    processingTime: parseFloat(randBetween(1.5, 8.0).toFixed(2)),
  };
}

// ============================================================
//  Service
// ============================================================

const DashboardService = {
  // ── 是否已初始化（防止每次刷新都重置） ──
  isInitialized(): boolean {
    return localStorage.getItem(KEYS.INITIALIZED) === 'true';
  },

  markInitialized(): void {
    localStorage.setItem(KEYS.INITIALIZED, 'true');
  },

  // ── 初始化模拟数据（仅首次或数据为空时） ──
  initializeSimulatedData(): void {
    if (this.isInitialized()) return;

    const now = Date.now();
    const day = 24 * 3600 * 1000;

    // 人物识别：生成7天数据
    const personRecords: PersonRecord[] = [];
    for (let d = 6; d >= 0; d--) {
      const count = randInt(30, 120);
      for (let i = 0; i < count; i++) {
        personRecords.push(generatePersonRecord(now - d * day - randBetween(0, day)));
      }
    }
    this.savePersonRecords(personRecords);

    // 路径规划：生成30天数据
    const routeRecords: RouteRecord[] = [];
    for (let d = 29; d >= 0; d--) {
      const count = randInt(2, 12);
      for (let i = 0; i < count; i++) {
        routeRecords.push(generateRouteRecord(now - d * day - randBetween(0, day)));
      }
    }
    this.saveRouteRecords(routeRecords);

    // 智能咨询：生成30天数据
    const consultationRecords: ConsultationRecord[] = [];
    for (let d = 29; d >= 0; d--) {
      const count = randInt(0, 5);
      for (let i = 0; i < count; i++) {
        consultationRecords.push(generateConsultationRecord(now - d * day - randBetween(0, day)));
      }
    }
    this.saveConsultationRecords(consultationRecords);

    // 无人机快照：生成7天数据（每小时一条）
    const droneSnapshots: DroneTelemetryRecord[] = [];
    for (let h = 24 * 7; h >= 0; h--) {
      droneSnapshots.push({
        id: 'fleet',
        timestamp: now - h * 3600 * 1000,
        battery: randBetween(40, 100),
        signal: randBetween(60, 100),
        speed: randBetween(0, 15),
        altitude: randBetween(50, 120),
        status: ['mission', 'idle', 'returning'][randInt(0, 2)],
      });
    }
    this.saveDroneSnapshots(droneSnapshots);

    this.markInitialized();
  },

  // ── 人物识别记录 ──
  getPersonRecords(): PersonRecord[] {
    return loadFromStorage(KEYS.PERSON_RECORDS, []);
  },

  addPersonRecord(record: Omit<PersonRecord, 'id' | 'timestamp'>): PersonRecord {
    const full: PersonRecord = {
      ...record,
      id: `person-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: Date.now(),
    };
    const records = this.getPersonRecords();
    records.push(full);
    this.savePersonRecords(trimRecords(records));
    return full;
  },

  savePersonRecords(records: PersonRecord[]): void {
    saveToStorage(KEYS.PERSON_RECORDS, records);
  },

  // ── 路径规划记录 ──
  getRouteRecords(): RouteRecord[] {
    return loadFromStorage(KEYS.ROUTE_RECORDS, []);
  },

  addRouteRecord(record: Omit<RouteRecord, 'id' | 'timestamp'>): RouteRecord {
    const full: RouteRecord = {
      ...record,
      id: `route-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: Date.now(),
    };
    const records = this.getRouteRecords();
    records.push(full);
    this.saveRouteRecords(trimRecords(records));
    return full;
  },

  saveRouteRecords(records: RouteRecord[]): void {
    saveToStorage(KEYS.ROUTE_RECORDS, records);
  },

  // ── 咨询记录 ──
  getConsultationRecords(): ConsultationRecord[] {
    return loadFromStorage(KEYS.CONSULTATION, []);
  },

  addConsultationRecord(record: Omit<ConsultationRecord, 'id' | 'timestamp'>): ConsultationRecord {
    const full: ConsultationRecord = {
      ...record,
      id: `consult-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: Date.now(),
    };
    const records = this.getConsultationRecords();
    records.push(full);
    this.saveConsultationRecords(trimRecords(records));
    return full;
  },

  saveConsultationRecords(records: ConsultationRecord[]): void {
    saveToStorage(KEYS.CONSULTATION, records);
  },

  // ── 无人机电量快照（用于时序图） ──
  getDroneSnapshots(): DroneTelemetryRecord[] {
    return loadFromStorage(KEYS.DRONE_SNAPSHOTS, []);
  },

  addDroneSnapshot(snapshot: Omit<DroneTelemetryRecord, 'timestamp'>): void {
    const records = this.getDroneSnapshots();
    records.push({ ...snapshot, timestamp: Date.now() });
    const oneWeek = 7 * 24 * 3600 * 1000;
    const cutoff = Date.now() - oneWeek;
    const trimmed = records.filter(r => r.timestamp > cutoff);
    saveToStorage(KEYS.DRONE_SNAPSHOTS, trimRecords(trimmed));
  },

  saveDroneSnapshots(records: DroneTelemetryRecord[]): void {
    saveToStorage(KEYS.DRONE_SNAPSHOTS, records);
  },

  // ── 聚合统计计算 ──
  computePersonStats(records: PersonRecord[]) {
    if (records.length === 0) return { total: 0, genderDist: {}, ageDist: {}, colorDist: {}, avgConfidence: 0, avgProcessingTime: 0 };

    const genderDist: Record<string, number> = {};
    const ageDist: Record<string, number> = {};
    const colorDist: Record<string, number> = {};
    let totalConfidence = 0;
    let totalProcessingTime = 0;

    records.forEach(r => {
      genderDist[r.gender] = (genderDist[r.gender] || 0) + 1;
      ageDist[r.age] = (ageDist[r.age] || 0) + 1;
      colorDist[r.upperColor] = (colorDist[r.upperColor] || 0) + 1;
      totalConfidence += r.confidence;
      totalProcessingTime += r.processingTime;
    });

    return {
      total: records.length,
      genderDist,
      ageDist,
      colorDist,
      avgConfidence: parseFloat((totalConfidence / records.length).toFixed(3)),
      avgProcessingTime: parseFloat((totalProcessingTime / records.length).toFixed(2)),
    };
  },

  computeRouteStats(records: RouteRecord[]) {
    if (records.length === 0) return { total: 0, totalDistance: 0, totalDuration: 0, strategyDist: {}, cityFrequency: {} };

    const strategyDist: Record<string, number> = {};
    const cityFrequency: Record<string, number> = {};
    let totalDistance = 0;

    records.forEach(r => {
      const label = STRATEGY_LABELS[r.strategy];
      strategyDist[label] = (strategyDist[label] || 0) + 1;
      totalDistance += parseFloat(r.distance);
      const cities = r.cities.split(' → ');
      cities.forEach(city => {
        cityFrequency[city] = (cityFrequency[city] || 0) + 1;
      });
    });

    return {
      total: records.length,
      totalDistance: parseFloat(totalDistance.toFixed(1)),
      totalDuration: records.reduce((s, r) => s + r.duration, 0),
      strategyDist,
      cityFrequency,
    };
  },

  computeConsultationStats(records: ConsultationRecord[]) {
    if (records.length === 0) return { total: 0, today: 0, typeDist: {}, statusDist: {}, avgProcessingTime: 0 };

    const today = new Date().toDateString();
    const typeDist: Record<string, number> = {};
    const statusDist: Record<string, number> = {};
    let todayCount = 0;
    let totalProcessingTime = 0;
    let processingCount = 0;

    records.forEach(r => {
      typeDist[r.interestLabel] = (typeDist[r.interestLabel] || 0) + 1;
      statusDist[r.status] = (statusDist[r.status] || 0) + 1;
      if (new Date(r.timestamp).toDateString() === today) todayCount++;
      if (r.processingTime) {
        totalProcessingTime += r.processingTime;
        processingCount++;
      }
    });

    return {
      total: records.length,
      today: todayCount,
      typeDist,
      statusDist,
      avgProcessingTime: processingCount > 0 ? parseFloat((totalProcessingTime / processingCount).toFixed(2)) : 0,
    };
  },

  // ── 清除所有数据（开发调试用） ──
  clearAllData(): void {
    Object.values(KEYS).forEach(key => localStorage.removeItem(key));
  },
};

export default DashboardService;

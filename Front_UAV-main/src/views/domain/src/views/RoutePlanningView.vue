<template>
  <div class="route-planning">
    <GuideSystem
      ref="guideSystem"
      @quick-action="handleQuickAction"
      @apply-suggestion="handleSuggestion"
    />
    <!-- 添加测试按钮 -->
    <el-button
      class="reset-guide-btn"
      @click="resetGuide"
    >
      重置引导
    </el-button>
    <!-- 左侧聊天对话框 -->
    <div class="chat-container">
      <div class="chat-header">
        <el-button
          type="success"
          size="small"
          class="new-route-btn"
          @click="createNewRoute"
          :icon="Plus"
        >
          新建路线
        </el-button>
      </div>
      <AIChatAssistant ref="chatAssistant" />
    </div>

    <!-- 右侧路线规划容器 -->
    <div class="route-container">
      <!-- 左侧路线信息面板 -->
      <div class="route-info-container">
        <!-- 推荐路线选择 -->
        <el-card class="route-card">
          <template #header>
            <div class="card-header">
              <h3>推荐路线</h3>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': !showRouteOptions }"
                @click="toggleRouteOptions"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <div class="route-options" :class="{ 'is-collapsed': !showRouteOptions }">
            <div
              v-for="(route, index) in routes"
              :key="route.type"
              class="route-option"
              :class="{ active: currentRouteIndex === index }"
              @click="selectRoute(index)"
            >
              <div class="option-content">
                <div class="option-header">
                  <span class="route-name">{{ route.name }}</span>
                  <el-tag size="small" :type="index === 0 ? 'success' : 'info'" effect="dark">
                    {{ index === 0 ? '推荐' : '备选' }}
                  </el-tag>
                </div>
                <div class="option-metrics">
                  <div class="metric">
                    <el-icon><Timer /></el-icon>
                    <span>{{ route.duration }}分钟</span>
                  </div>
                  <div class="metric">
                    <el-icon><Place /></el-icon>
                    <span>{{ route.distance }}公里</span>
                  </div>
                  <div class="metric">
                    <el-icon><Money /></el-icon>
                    <span>{{ route.toll || 0 }}元</span>
                  </div>
                </div>
                <div class="option-reason">{{ route.reason }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 路线详情 -->
        <el-card class="route-card" v-if="routeInfo">
          <template #header>
            <div class="card-header">
              <h3>路线详情</h3>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': !showRouteSummary }"
                @click="toggleRouteSummary"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <div class="route-details" :class="{ 'is-collapsed': !showRouteSummary }">
            <div class="detail-grid">
              <div class="detail-item">
                <div class="item-label">
                  <el-icon><Location /></el-icon>
                  <span>起点</span>
                </div>
                <div class="item-value">{{ routeInfo.start_point }}</div>
              </div>
              <div class="detail-item">
                <div class="item-label">
                  <el-icon><Position /></el-icon>
                  <span>终点</span>
                </div>
                <div class="item-value">{{ routeInfo.end_point }}</div>
              </div>
              <div class="detail-item">
                <div class="item-label">
                  <el-icon><Timer /></el-icon>
                  <span>预计用时</span>
                </div>
                <div class="item-value">{{ routeInfo.duration }}分钟</div>
              </div>
              <div class="detail-item">
                <div class="item-label">
                  <el-icon><Place /></el-icon>
                  <span>总距离</span>
                </div>
                <div class="item-value">{{ routeInfo.distance }}公里</div>
              </div>
              <div class="detail-item">
                <div class="item-label">
                  <el-icon><Money /></el-icon>
                  <span>过路费</span>
                </div>
                <div class="item-value">{{ routeInfo.toll || '0' }}元</div>
              </div>
              <div class="detail-item">
                <div class="item-label">
                  <el-icon><Warning /></el-icon>
                  <span>限行</span>
                </div>
                <div class="item-value">{{ routeInfo.restriction ? '有限行' : '无限行' }}</div>
              </div>
            </div>
            <div class="detail-footer">
              <div v-if="routeInfo.waypoints?.length" class="footer-item">
                <div class="item-label">
                  <el-icon><Connection /></el-icon>
                  <span>途经点</span>
                </div>
                <div class="item-value">{{ routeInfo.waypoints.join(' → ') }}</div>
              </div>
              <div class="footer-item">
                <div class="item-label">
                  <el-icon><Location /></el-icon>
                  <span>途经城市</span>
                </div>
                <div class="item-value">{{ routeInfo.cities || '加载中...' }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 导航详情面板 -->
        <div class="route-panel custom-scrollbar">
          <div id="panel" class="panel-content"></div>
        </div>
      </div>

      <!-- 右侧地图容器 -->
      <div class="map-wrapper">
        <div id="container" class="map-container"></div>

        <!-- 图层控制面板 -->
        <el-card class="layer-control">
          <template #header>
            <div class="card-header">
              <el-icon><Monitor /></el-icon>
              <span>图层控制</span>
            </div>
          </template>
          <div class="layer-content">
            <div class="layer-item">
              <el-switch
                v-model="showTraffic"
                @change="toggleTraffic"
                active-text="实时路况"
              />
              <div class="traffic-legend" v-if="showTraffic">
                <div class="legend-item">
                  <span class="color-block smooth"></span>
                  <span>畅通</span>
                </div>
                <div class="legend-item">
                  <span class="color-block slow"></span>
                  <span>缓行</span>
                </div>
                <div class="legend-item">
                  <span class="color-block congested"></span>
                  <span>拥堵</span>
                </div>
              </div>
            </div>
            <div class="layer-item">
              <el-switch
                v-model="showSatellite"
                @change="toggleSatellite"
                active-text="卫星图像"
              />
            </div>
            <div class="layer-item">
              <el-switch
                v-model="showBuildings"
                @change="toggleBuildings"
                active-text="3D建筑"
              />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount, nextTick, onActivated } from 'vue'
import { useMainStore } from '../stores'
import { ElMessage, ElLoading, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import AIChatAssistant from '../components/AIChatAssistant.vue'
import GuideSystem from '../components/GuideSystem.vue'
import {
  Location, Position, Timer, Place, Money,
  Warning, Connection, ArrowDown,
  Monitor,
  Sunny,
  Plus
} from '@element-plus/icons-vue'
import citiesData from '../assets/data/cities.json'

const store = useMainStore()
const map = ref(null)
const driving = ref(null)
const isMapReady = ref(false)
const currentRoutes = ref([])
const routes = ref([
  {
    name: '推荐路线 (最快)',
    type: 'fastest',
    duration: '--',
    distance: '--',
    toll: '--',
    reason: '根据历史数据，选择最快的路线。'
  },
  {
    name: '备选路线 (经济)',
    type: 'economic',
    duration: '--',
    distance: '--',
    toll: '--',
    reason: '考虑费用，选择经济的路线。'
  }
])
const currentRouteIndex = ref(0)
const showRouteOptions = ref(true)
const showRouteSummary = ref(true)
const routeInfo = ref(null)

// 图层控制
const showTraffic = ref(false)
const showSatellite = ref(false)
const show3D = ref(false)
const showBuildings = ref(true)

// 折叠面板激活的项
const activeCollapse = ref(['routes', 'summary'])

// 监听聊天消息中的路线数据
watch(() => store.chatHistory, async (messages) => {
  if (!messages || messages.length === 0) return;

  try {
    const lastMessage = messages[messages.length - 1];
    console.log('检测到聊天历史更新，最新消息:', lastMessage);

    if (lastMessage?.route_data) {
      console.log('发现路线数据:', lastMessage.route_data);

      let normalizedRouteData = lastMessage.route_data;
      try {
        if (typeof normalizedRouteData === 'string') {
          try {
            normalizedRouteData = JSON.parse(normalizedRouteData);
          } catch (e) {
            normalizedRouteData = { response_text: normalizedRouteData };
          }
        }

        const ensureRouteInfo = (rd) => {
          if (!rd.route_info) rd.route_info = {};
          const ri = rd.route_info;
          const candidates = [
            rd.response_text || '',
            rd.route_text || '',
            lastMessage.content || ''
          ].join(' ');

          if ((!ri.start_point || ri.start_point === '未知') || (!ri.end_point || ri.end_point === '未知')) {
            const m = candidates.match(/从\s*([^到至,，\s]+)\s*[到至]\s*([^,，\s]+)/);
            if (m && m[1] && m[2]) {
              ri.start_point = ri.start_point && ri.start_point !== '未知' ? ri.start_point : m[1].trim();
              ri.end_point = ri.end_point && ri.end_point !== '未知' ? ri.end_point : m[2].trim();
            } else {
              if (candidates.includes('到')) {
                const parts = candidates.split('到').map(p => p.replace(/[\n\r]/g, '').trim()).filter(Boolean);
                if (parts.length >= 2) {
                  ri.start_point = ri.start_point && ri.start_point !== '未知' ? ri.start_point : parts[0];
                  ri.end_point = ri.end_point && ri.end_point !== '未知' ? ri.end_point : parts[1];
                }
              }
            }
          }

          ri.start_point = ri.start_point || '未知';
          ri.end_point = ri.end_point || '未知';
          rd.route_info = ri;
          return rd;
        };

        normalizedRouteData = ensureRouteInfo(normalizedRouteData);
      } catch (e) {
        console.warn('标准化 route_data 失败，使用原始数据', e);
      }

      console.log('标准化后的路线数据:', normalizedRouteData);

      const mapReady = await ensureMapReady();
      if (!mapReady) {
        console.error('地图初始化失败，无法处理路线数据');
        ElMessage.error('地图组件加载失败，请刷新页面');
        return;
      }

      await nextTick();

      const mapContainer = document.getElementById('container');
      if (!mapContainer) {
        console.error('地图容器元素不存在');
        ElMessage.error('页面元素加载异常，请刷新页面');
        return;
      }

      let attempts = 0;
      const maxAttempts = 3;
      const tryHandleRouteData = async () => {
        try {
          console.log(`尝试处理路线数据 (${attempts + 1}/${maxAttempts})...`);
          await handleRouteData(normalizedRouteData);
          console.log('路线数据处理成功');
        } catch (error) {
          console.error('路线数据处理失败:', error);
          attempts++;

          if (attempts < maxAttempts) {
            console.log(`${1000 * attempts}毫秒后重试...`);
            setTimeout(tryHandleRouteData, 1000 * attempts);
          } else {
            ElMessage.error('路线规划失败，请重试');
          }
        }
      };

      tryHandleRouteData();
    }
  } catch (error) {
    console.error('监听聊天历史出错:', error);
  }
}, { deep: true });

watch(() => store.loadSelectedRecord, (loadRecord) => {
  if (loadRecord) {
    console.log('检测到来自父组件的路线加载请求');
    loadSelectedRouteRecord();
    store.loadSelectedRecord = false;
  }
}, { immediate: true });

const route = useRoute()
const chatAssistant = ref(null)

onMounted(async () => {
  console.log('组件挂载，开始初始化地图...');
  const mapInitialized = await ensureMapReady();

  if (!mapInitialized) {
    console.error('地图初始化失败，尝试延迟再次初始化');
    setTimeout(async () => {
      if (await ensureMapReady()) {
        console.log('延迟初始化地图成功');
      } else {
        console.error('多次尝试初始化地图失败');
        ElMessage.error('地图加载失败，请刷新页面');
      }
    }, 2000);
  }

  const pageRefresh = sessionStorage.getItem('routePlanningRefresh') === null;
  sessionStorage.setItem('routePlanningRefresh', 'false');

  if (pageRefresh) {
    console.log('检测到页面刷新，保存并创建新路线');

    nextTick(async () => {
      if (routeInfo.value) {
        await saveCurrentRoute();
        ElMessage.success('已自动保存上一次的路线规划');
      }

      resetRouteAndChat();
      ElMessage.info('页面已刷新，已为您创建新路线');
    });
  }
  else if (!store.routeSessionStartTime) {
    store.startNewRouteSession();
  }

  if (route.query.loadRecord === 'true') {
    loadSelectedRouteRecord();
  }

  window.addEventListener('beforeunload', handleBeforeUnload);
  window.addEventListener('resize', handleWindowResize);
});

const handleWindowResize = () => {
  if (map.value) {
    console.log('窗口大小变化，调整地图尺寸');
    nextTick(() => {
      map.value.resize();
    });
  }
};

const initMap = async () => {
  try {
    await nextTick();

    const mapContainer = document.getElementById('container');
    if (!mapContainer) {
      console.error('地图容器不存在，无法初始化地图');
      ElMessage.error('地图容器加载失败，请刷新页面');
      return false;
    }

    console.log('开始初始化地图，容器尺寸:', mapContainer.offsetWidth, mapContainer.offsetHeight);

    if (mapContainer.offsetWidth === 0 || mapContainer.offsetHeight === 0) {
      mapContainer.style.width = '100%';
      mapContainer.style.height = '600px';
      console.log('强制设置地图容器尺寸');
    }

    if (typeof AMap === 'undefined') {
      console.error('AMap对象未定义，可能是地图JS未加载');
      ElMessage.error('地图组件未加载，请检查网络连接');
      return false;
    }

    await new Promise((resolve) => {
      if (typeof AMap.Geocoder === 'function') {
        console.log('地理编码插件已加载');
        resolve(true);
        return;
      }

      console.log('正在加载地理编码插件...');
      AMap.plugin(['AMap.Geocoder'], function() {
        console.log('地理编码插件加载完成');
        resolve(true);
      });
    });

    map.value = new AMap.Map('container', {
      zoom: 10,
      center: [116.397428, 39.90923],
      viewMode: '2D'
    });

    console.log('地图实例创建成功:', map.value);

    driving.value = new AMap.Driving({
      map: map.value,
      policy: AMap.DrivingPolicy.LEAST_TIME,
      panel: 'panel'
    });

    map.value.on('complete', () => {
      console.log('地图加载完成');
      isMapReady.value = true;
    });

    return true;
  } catch (error) {
    console.error('初始化地图失败:', error);
    ElMessage.error(`初始化地图失败: ${error.message || String(error)}`);
    return false;
  }
};

const ensureMapReady = async () => {
  if (!isMapReady.value || !map.value || !driving.value) {
    console.log('地图未初始化，开始初始化...');
    return await initMap();
  }
  return true;
}

const clearRoutes = () => {
  if (driving.value) {
    driving.value.clear();
  }

  if (map.value && currentRoutes.value.length > 0) {
    currentRoutes.value.forEach(route => {
      if (route) map.value.remove(route);
    });
    currentRoutes.value = [];

    map.value.clearMap();
  }

  console.log('已清除所有路线和标记');
}

const selectRoute = async (index) => {
  if (currentRouteIndex.value === index) return

  currentRouteIndex.value = index
  ElMessage.info('正在计算路线详情...')

  clearRoutes()

  if (routeInfo.value) {
    try {
      await handleRouteData({
        route_info: {
          start_point: routeInfo.value.start_point,
          end_point: routeInfo.value.end_point,
          waypoints: routeInfo.value.waypoints || []
        }
      })
    } catch (error) {
      console.error('路线切换失败:', error)
      ElMessage.error('路线切换失败，请重试')
    }
  }
}

const calculateRoute = (routeData, routeType, routeIndex = currentRouteIndex.value) => {
  if (!driving.value || !routeData || !isMapReady.value) return

  console.log('开始规划路线:', { routeData, routeType, routeIndex })

  const { start_point, end_point, waypoints } = routeData

  driving.value.clear()
  map.value.clearMap()

  const policyMap = {
    'LEAST_TIME': AMap.DrivingPolicy.LEAST_TIME,
    'LEAST_FEE': AMap.DrivingPolicy.LEAST_FEE,
    'LEAST_DISTANCE': AMap.DrivingPolicy.LEAST_DISTANCE,
    'REAL_TRAFFIC': AMap.DrivingPolicy.REAL_TRAFFIC
  }

  const policy = policyMap[routeType] || AMap.DrivingPolicy.LEAST_TIME
  driving.value.setPolicy(policy)

  const geocoder = new AMap.Geocoder({
    city: "全国"
  })

  geocoder.getLocation(start_point, (status, result) => {
    if (status === 'complete' && result.geocodes.length) {
      const startLoc = result.geocodes[0].location

      geocoder.getLocation(end_point, (status, result) => {
        if (status === 'complete' && result.geocodes.length) {
          const endLoc = result.geocodes[0].location

          const getWayPointPromises = waypoints.map(point => {
            return new Promise((resolve) => {
              geocoder.getLocation(point, (status, result) => {
                if (status === 'complete' && result.geocodes.length) {
                  resolve(result.geocodes[0].location)
                } else {
                  resolve(null)
                }
              })
            })
          })

          Promise.all(getWayPointPromises).then(wayPointLocs => {
            const validWayPoints = wayPointLocs.filter(loc => loc !== null)

            driving.value.search(
              startLoc,
              endLoc,
              {
                waypoints: validWayPoints
              },
              (status, result) => {
                if (status === 'complete' && result.routes && result.routes.length) {
                  const route = result.routes[0]

                  if (routeIndex === currentRouteIndex.value) {
                    routeInfo.value = {
                      ...routeData,
                      distance: (route.distance / 1000).toFixed(1),
                      duration: Math.ceil(route.time / 60),
                      toll: route.tolls || 0,
                      restriction: route.restriction ? '有限行' : '无限行',
                      cities: Array.from(new Set(route.steps.map(step => step.city))).join(' → ')
                    }
                  }

                  routes.value[routeIndex] = {
                    ...routes.value[routeIndex],
                    distance: (route.distance / 1000).toFixed(1),
                    duration: Math.ceil(route.time / 60),
                    toll: route.tolls || 0
                  }
                } else {
                  console.error('路线规划失败:', result)
                  ElMessage.error('路线规划失败，请重试')
                }
              }
            )
          })
        }
      })
    }
  })
}

onBeforeUnmount(() => {
  if (map.value) {
    map.value.destroy()
    map.value = null
  }
  if (driving.value) {
    driving.value.clear()
    driving.value = null
  }

  window.removeEventListener('beforeunload', handleBeforeUnload)
})

const toggleRouteOptions = () => {
  showRouteOptions.value = !showRouteOptions.value
}

const toggleRouteSummary = () => {
  showRouteSummary.value = !showRouteSummary.value
}

const toggleTraffic = (value) => {
  if (map.value) {
    if (value) {
      const trafficLayer = new AMap.TileLayer.Traffic()
      map.value.add(trafficLayer)
      map.value._trafficLayer = trafficLayer
    } else {
      if (map.value._trafficLayer) {
        map.value.remove(map.value._trafficLayer)
        map.value._trafficLayer = null
      }
    }
  }
}

const toggleSatellite = (value) => {
  if (map.value) {
    if (value) {
      const satelliteLayer = new AMap.TileLayer.Satellite()
      map.value.add(satelliteLayer)
      map.value._satelliteLayer = satelliteLayer
    } else {
      if (map.value._satelliteLayer) {
        map.value.remove(map.value._satelliteLayer)
        map.value._satelliteLayer = null
      }
    }
  }
}

const toggleBuildings = (value) => {
  if (map.value) {
    if (value) {
      const buildingsLayer = new AMap.Buildings({
        zooms: [16, 20],
        zIndex: 10
      })
      map.value.add(buildingsLayer)
      map.value._buildingsLayer = buildingsLayer
    } else {
      if (map.value._buildingsLayer) {
        map.value.remove(map.value._buildingsLayer)
        map.value._buildingsLayer = null
      }
    }
  }
}

const toggle3D = (value) => {
  if (map.value) {
    map.value.setFeatures(value ? ['bg', 'building', 'point'] : ['bg', 'point'])
  }
}

const handleQuickAction = async (action) => {
  try {
    const requestParams = {
      text: action.prompt
        .replace('{start}', '北京西站')
        .replace('{end}', '首都机场')
        .replace('{spots}', '郑州工程技术学院'),
      type: action.id
    }

    const response = await store.sendChatMessage(requestParams)

    if (response.success && response.route_data) {
      if (!isMapReady.value) {
        await initMap()
      }

      clearRoutes()

      const routeData = response.route_data

      const recommendedRoutes = routeData.recommended_routes || []
      routes.value = recommendedRoutes.map(route => ({
        ...route,
        duration: 0,
        distance: 0,
        toll: 0
      }))

      if (routes.value.length > 0) {
        currentRouteIndex.value = 0
        await calculateRoute(routeData.route_info, routes.value[0].type)

        if (routes.value[1]) {
          await calculateRoute(routeData.route_info, routes.value[1].type, 1)
        }
      }
    }
  } catch (error) {
    console.error('路线规划失败:', error)
    ElMessage.error('路线规划失败，请重试')
  }
}

const handleSuggestion = (suggestion) => {
  console.log('Selected suggestion:', suggestion)
}

const guideSystem = ref(null)

const resetGuide = () => {
  guideSystem.value?.resetGuide()
}

const getCityName = (adcode) => {
  const cityInfo = citiesData[adcode]
  return cityInfo ? cityInfo.name : adcode
}

const handleRouteData = async (routeData) => {
  if (!await ensureMapReady()) {
    console.error('地图未准备好，无法处理路线数据');
    ElMessage.error('地图组件未准备好，请刷新页面重试');
    return;
  }

  console.log('地图组件准备就绪，开始处理路线数据');

  clearRoutes();

  if (!routeData || !routeData.route_info) {
    console.error('无效的路线数据:', routeData);
    ElMessage.error('路线数据无效');
    return;
  }

  console.log('接收到的路线数据:', routeData);

  const routeContainer = document.querySelector('.route-container');
  const mapContainer = document.getElementById('container');

  if (!routeContainer || !mapContainer) {
    console.error('找不到路线容器或地图容器');
    ElMessage.error('页面元素异常，请刷新页面');
    return;
  }

  console.log('路线容器尺寸:', routeContainer.clientWidth, routeContainer.clientHeight);
  console.log('地图容器尺寸:', mapContainer.clientWidth, mapContainer.clientHeight);

  if (mapContainer.clientWidth === 0 || mapContainer.clientHeight === 0) {
    mapContainer.style.width = '100%';
    mapContainer.style.height = '600px';
    console.log('强制设置地图容器尺寸');
    map.value && map.value.resize();
  }

  routes.value = [
    {
      name: '推荐路线 (最快)',
      type: 'fastest',
      duration: '计算中...',
      distance: '计算中...',
      toll: '计算中...',
      reason: '根据历史数据，选择最快的路线。'
    },
    {
      name: '备选路线 (经济)',
      type: 'economic',
      duration: '计算中...',
      distance: '计算中...',
      toll: '计算中...',
      reason: '考虑费用，选择经济的路线。'
    }
  ];

  const { start_point, end_point, waypoints = [] } = routeData.route_info;

  try {
    console.log('开始地址解析: 起点=', start_point, '终点=', end_point, '途经点=', waypoints);

    if (typeof AMap.Geocoder !== 'function') {
      console.log('Geocoder插件未加载，尝试加载插件...');
      await new Promise((resolve) => {
        AMap.plugin(['AMap.Geocoder'], function() {
          console.log('Geocoder插件加载完成');
          resolve(true);
        });
      });
    }

    const geocoder = new AMap.Geocoder({
      city: "全国"
    });

    const startResult = await new Promise((resolve, reject) => {
      geocoder.getLocation(start_point, (status, result) => {
        console.log('起点地址解析结果:', status, result);
        if (status === 'complete' && result.geocodes.length) {
          resolve(result.geocodes[0].location);
        } else {
          reject(new Error('起点地址解析失败'));
        }
      });
    });

    const endResult = await new Promise((resolve, reject) => {
      geocoder.getLocation(end_point, (status, result) => {
        console.log('终点地址解析结果:', status, result);
        if (status === 'complete' && result.geocodes.length) {
          resolve(result.geocodes[0].location);
        } else {
          reject(new Error('终点地址解析失败'));
        }
      });
    });

    const waypointPromises = waypoints.map(point =>
      new Promise((resolve, reject) => {
        if (!point) {
          resolve(null);
          return;
        }
        geocoder.getLocation(point.toString(), (status, result) => {
          console.log(`途经点 ${point} 地址解析结果:`, status, result);
          if (status === 'complete' && result.geocodes.length) {
            resolve(result.geocodes[0].location);
          } else {
            console.warn(`途经点 ${point} 地址解析失败`);
            resolve(null);
          }
        });
      })
    );

    const waypointResults = await Promise.all(waypointPromises);
    const validWaypoints = waypointResults.filter(Boolean);
    console.log('有效途经点:', validWaypoints);

    if (!map.value || !driving.value) {
      throw new Error('地图或驾驶实例无效，可能已被销毁');
    }

    console.log('开始规划路线:', {
      start: startResult,
      end: endResult,
      waypoints: validWaypoints
    });

    await new Promise((resolve, reject) => {
      try {
        map.value.clearMap();
        driving.value.clear();

        const loading = ElLoading.service({
          target: '.map-wrapper',
          text: '正在规划路线...'
        });

        driving.value.search(
          startResult,
          endResult,
          {
            waypoints: validWaypoints,
            extensions: 'all',
            showTraffic: true,
            policy: AMap.DrivingPolicy.LEAST_TIME
          },
          (status, result) => {
            loading.close();

            console.log('路线规划结果状态:', status);

            if (status === 'complete') {
              console.log('路线规划成功:', result);

              if (result.routes && result.routes.length) {
                const route = result.routes[0];
                console.log('获取到的路线:', route);

                try {
                  const polyline = new AMap.Polyline({
                    path: route.steps.map(step => step.path).flat(),
                    strokeColor: "#00B96B",
                    strokeWeight: 6,
                    strokeOpacity: 0.8,
                    zIndex: 50
                  });

                  map.value.add(polyline);
                  currentRoutes.value.push(polyline);

                  map.value.setFitView();

                  const citiesList = [];
                  if (route.steps) {
                    route.steps.forEach(step => {
                      if (step.city && !citiesList.includes(step.city)) {
                        const cityName = getCityName(step.city);
                        if (cityName) {
                          citiesList.push(cityName);
                        }
                      }
                    });
                  }

                  const fallbackCities = [
                    start_point,
                    ...(waypoints || []),
                    end_point
                  ].filter(Boolean);
                  const citiesText = citiesList.length > 0
                    ? citiesList.join(' → ')
                    : (fallbackCities.length > 0 ? fallbackCities.join(' → ') : '加载中...');

                  console.log('途经城市列表:', citiesList, '最终显示:', citiesText);

                  const routeDetails = {
                    duration: Math.round(route.time / 60),
                    distance: (route.distance / 1000).toFixed(1),
                    toll: route.tolls || 0
                  };

                  console.log('路线详情:', routeDetails);

                  routes.value[currentRouteIndex.value] = {
                    ...routes.value[currentRouteIndex.value],
                    ...routeDetails
                  };

                  if (currentRouteIndex.value === 0) {
                    routes.value[1] = {
                      ...routes.value[1],
                      duration: Math.round(route.time * 1.2 / 60),
                      distance: (route.distance * 1.1 / 1000).toFixed(1),
                      toll: Math.max(0, (route.tolls || 0) * 0.8)
                    };
                  }

                  routeInfo.value = {
                    start_point: start_point,
                    end_point: end_point,
                    ...routeDetails,
                    restriction: false,
                    cities: citiesText,
                    waypoints: waypoints
                  };

                  console.log('已更新路线详情对象:', routeInfo.value);

                  ElMessage.success('路线规划成功');

                  setTimeout(() => {
                    if (map.value) {
                      map.value.resize();
                      map.value.setFitView();
                    }
                  }, 300);

                  resolve(true);
                } catch (renderError) {
                  console.error('路线渲染失败:', renderError);
                  reject(new Error('路线渲染失败: ' + renderError.message));
                }
              } else {
                console.error('路线规划结果中没有路线数据:', result);
                reject(new Error('未找到可行的路线'));
              }
            } else {
              console.error('路线规划失败:', result);
              reject(new Error('路线规划失败: ' + status));
            }
          }
        );
      } catch (searchError) {
        console.error('执行路线搜索时出错:', searchError);
        reject(searchError);
      }
    });

    nextTick(() => {
      if (map.value) {
        map.value.resize();
      }
    });

  } catch (error) {
    console.error('地址解析或路线规划失败:', error);
    ElMessage.error('路线规划失败: ' + (error.message || '未知错误'));

    routes.value = routes.value.map(route => ({
      ...route,
      duration: '--',
      distance: '--',
      toll: '--'
    }));
  }
}

const showLoading = () => {
  return ElLoading.service({
    target: '.map-wrapper',
    text: '地图加载中...'
  })
}

const createNewRoute = () => {
  if (routeInfo.value) {
    ElMessageBox.confirm(
      '创建新路线将清除当前的路线规划记录，是否保存当前路线?',
      '保存路线记录',
      {
        confirmButtonText: '保存并创建',
        cancelButtonText: '不保存，直接创建',
        distinguishCancelAndClose: true,
        type: 'warning'
      }
    ).then(() => {
      saveCurrentRoute().then(() => {
        resetRouteAndChat()
      })
    }).catch((action) => {
      if (action === 'cancel') {
        resetRouteAndChat()
      }
    })
  } else {
    resetRouteAndChat()
  }
}

const resetRouteAndChat = () => {
  store.startNewRouteSession()

  clearRoutes()

  routeInfo.value = null

  routes.value = [
    {
      name: '推荐路线 (最快)',
      type: 'fastest',
      duration: '--',
      distance: '--',
      toll: '--',
      reason: '根据历史数据，选择最快的路线。'
    },
    {
      name: '备选路线 (经济)',
      type: 'economic',
      duration: '--',
      distance: '--',
      toll: '--',
      reason: '考虑费用，选择经济的路线。'
    }
  ]

  ElMessage.success('已创建新路线，请开始规划')
}

const saveCurrentRoute = async () => {
  if (!routeInfo.value) return false

  const success = store.saveRouteRecord(routeInfo.value)

  if (success) {
    ElMessage.success('路线记录保存成功')
  } else {
    ElMessage.error('保存路线记录失败')
  }

  return success
}

const loadSelectedRouteRecord = () => {
  const record = store.loadSelectedRouteRecord()
  if (!record) return false

  if (record.routeInfo) {
    nextTick(() => {
      handleRouteData({
        route_info: record.routeInfo
      })
    })
    ElMessage.success('已加载路线记录')
  }

  return true
}

const handleBeforeUnload = (e) => {
  console.log("检测到页面刷新，保存并创建新路线");
  if (routeInfo.value) {
    try {
      saveCurrentRoute();
    } catch (err) {
      console.error('自动保存路线失败:', err);
    }
  }
};

onBeforeUnmount(() => {
  if (routeInfo.value) {
    saveCurrentRoute();
  }

  window.removeEventListener('beforeunload', handleBeforeUnload);
  window.removeEventListener('resize', handleWindowResize);

  if (map.value) {
    map.value.destroy();
    map.value = null;
  }
  if (driving.value) {
    driving.value.clear();
    driving.value = null;
  }
});

onActivated(() => {
  if (routeInfo.value) {
    handleRouteData({
      route_info: {
        start_point: routeInfo.value.start_point,
        end_point: routeInfo.value.end_point,
        waypoints: routeInfo.value.waypoints || []
      }
    })
  }
})
</script>

<style scoped>
.route-planning {
  display: flex;
  height: 100%;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.chat-container {
  width: 400px;
  flex-shrink: 0;
}

.route-container {
  flex: 1;
  display: flex;
  gap: 20px;
  min-width: 0;
  position: relative;
  overflow: visible;
}

.route-info-container {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 10;
}

.route-card {
  background: var(--el-bg-color-overlay);
  border: none;
  box-shadow: var(--el-box-shadow-light);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.route-option {
  padding: 16px;
  border-radius: 8px;
  background: var(--el-bg-color);
  cursor: pointer;
  transition: all 0.3s;
}

.route-option:hover {
  transform: translateY(-2px);
  box-shadow: var(--el-box-shadow-light);
}

.route-option.active {
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary);
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.route-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.option-metrics {
  display: flex;
  gap: 16px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-text-color-regular);
}

.option-reason {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.item-value {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.detail-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footer-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.route-panel {
  flex: 1;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
  overflow-y: auto;
  overflow-x: hidden;
  box-shadow: var(--el-box-shadow-light);
}

.map-wrapper {
  position: relative;
  flex: 1;
  overflow-x: hidden;
  max-height: calc(100vh - 180px);
  border-radius: 8px;
  overflow: hidden;
  z-index: 5;
}

.map-container {
  width: 100% !important;
  height: 100% !important;
  background: var(--el-bg-color-overlay);
}

.layer-control {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 280px;
  background: var(--el-bg-color-overlay);
  border: none;
  backdrop-filter: blur(10px);
}

.layer-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.layer-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.traffic-legend {
  display: flex;
  gap: 16px;
  margin-left: 36px;
  margin-top: 4px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.color-block {
  width: 16px;
  height: 3px;
  border-radius: 1.5px;
}

.smooth { background: var(--el-color-success); }
.slow { background: var(--el-color-warning); }
.congested { background: var(--el-color-danger); }

.collapse-icon {
  cursor: pointer;
  transition: transform 0.3s ease;
}

.collapse-icon.is-collapsed {
  transform: rotate(-180deg);
}

.route-options,
.route-details {
  transition: all 0.3s ease-in-out;
  max-height: 2000px;
  opacity: 1;
  overflow: hidden;
  padding: 20px;
}

.route-options.is-collapsed,
.route-details.is-collapsed {
  max-height: 0;
  opacity: 0;
  margin: 0;
  padding: 0;
}

.el-card__body {
  transition: padding 0.3s ease-in-out;
}

.el-card__body:has(.is-collapsed) {
  padding: 0;
}

.reset-guide-btn {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
}

:deep(.amap-logo) {
  opacity: 0.8 !important;
  z-index: 10 !important;
}

:deep(.amap-copyright) {
  opacity: 0.8 !important;
  z-index: 10 !important;
}

:deep(.amap-marker) {
  z-index: 111 !important;
}

:deep(.amap-marker-label) {
  z-index: 112 !important;
  border: 1px solid var(--el-color-primary);
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
  padding: 4px 8px;
}

:deep(.amap-info-content) {
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
  border-radius: 4px;
  padding: 8px;
}

:deep(#panel) {
  padding: 16px;
  background: transparent !important;
  border-radius: 4px;
  overflow-y: auto;
}

.chat-header {
  display: flex;
  justify-content: flex-end;
  padding: 0 0 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 12px;
}

.new-route-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: var(--el-border-color-lighter) transparent;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--el-border-color-lighter);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: var(--el-border-color);
}

:deep(#panel .amap-lib-driving) {
  border-radius: 8px;
  background: var(--el-bg-color) !important;
}

:deep(#panel .amap-lib-driving .planTitle) {
  background: var(--el-color-primary-light-9) !important;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding: 12px 16px !important;
  border-radius: 8px 8px 0 0;
}

:deep(#panel .amap-lib-driving .plan) {
  padding: 16px !important;
  border-bottom: 1px solid var(--el-border-color-lighter) !important;
}

:deep(#panel .amap-lib-driving .plan:last-child) {
  border-bottom: none !important;
}

:deep(#panel .amap-lib-driving .route-section) {
  padding: 8px 0 !important;
  border-bottom: 1px dashed var(--el-border-color-lighter) !important;
}

:deep(#panel .amap-lib-driving .route-section:last-child) {
  border-bottom: none !important;
}

:deep(#panel .amap-lib-driving .route-section-content) {
  color: var(--el-text-color-regular) !important;
}

:deep(#panel .amap-lib-driving .route-section-icon) {
  background-color: var(--el-color-primary-light-8) !important;
  border-radius: 4px;
}

:deep(#panel .amap-lib-driving .route-section-distance) {
  color: var(--el-text-color-secondary) !important;
}

:deep(.amap-lib-driving-route) {
  stroke-width: 6px !important;
  stroke: #00B96B !important;
}

:deep(.amap-lib-driving-route:hover) {
  stroke-width: 8px !important;
  animation: routePulse 1.5s infinite;
}

@keyframes routePulse {
  0% { stroke-opacity: 0.8; }
  50% { stroke-opacity: 1; }
  100% { stroke-opacity: 0.8; }
}
</style>

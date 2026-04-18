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
import { useMainStore } from '@/stores'
import { ElMessage, ElLoading, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import AIChatAssistant from '@/components/AIChatAssistant.vue'
import GuideSystem from '@/components/GuideSystem.vue'
import { 
  Location, Position, Timer, Place, Money, 
  Warning, Connection, ArrowDown,
  Monitor,
  Sunny,
  Plus
} from '@element-plus/icons-vue'
import citiesData from '@/../../qq/cities.json'

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
  const lastMessage = messages[messages.length - 1]
  if (lastMessage?.route_data) {
    // 确保地图已初始化
    if (!isMapReady.value) {
      await initMap()
    }
    
    // 处理路线数据
    const routeData = lastMessage.route_data
    handleRouteData(routeData)
  }
}, { deep: true })

const route = useRoute()
const chatAssistant = ref(null)

// 在组件挂载时检查是否需要加载路线记录或是页面刷新
onMounted(async () => {
  await initMap()
  
  // 检查是否是页面刷新
  const pageRefresh = sessionStorage.getItem('routePlanningRefresh') === null;
  // 设置标记，下次刷新时可以检测到
  sessionStorage.setItem('routePlanningRefresh', 'false');
  
  // 如果是页面刷新，先保存当前路线，然后创建新路线
  if (pageRefresh) {
    console.log('检测到页面刷新，保存并创建新路线');
    
    // 延迟执行，确保路线信息已经加载
    nextTick(async () => {
      // 如果有路线信息，先保存
      if (routeInfo.value) {
        await saveCurrentRoute();
        ElMessage.success('已自动保存上一次的路线规划');
      }
      
      // 然后重置创建新路线
      resetRouteAndChat();
      ElMessage.info('页面已刷新，已为您创建新路线');
    });
  }
  // 否则开始新的路线规划会话（如果之前没有开始过的话）
  else if (!store.routeSessionStartTime) {
    store.startNewRouteSession()
  }
  
  // 如果有加载记录的参数，尝试加载选中的记录
  if (route.query.loadRecord === 'true') {
    loadSelectedRouteRecord()
  }

  // 注册页面刷新事件，确保用户刷新页面时保存路线
  window.addEventListener('beforeunload', handleBeforeUnload)
})

// 初始化地图
const initMap = () => {
  try {
    // 创建地图实例，设置默认中心点为北京
    map.value = new AMap.Map('container', {
      zoom: 12,
      center: [116.397428, 39.90923], // 默认中心点坐标
      viewMode: '3D'
    })
    
    // 创建驾车导航实例
    driving.value = new AMap.Driving({
      map: map.value,
      panel: 'panel',
      autoFitView: true
    })
    
    isMapReady.value = true
  } catch (error) {
    console.error('地图初始化失败:', error)
    ElMessage.error('地图初始化失败，请刷新页面重试')
  }
}

// 清除现有路线
const clearRoutes = () => {
  if (driving.value) {
    driving.value.clear()
  }
  currentRoutes.value.forEach(route => {
    map.value?.remove(route)
  })
  currentRoutes.value = []
}

// 选择路线
const selectRoute = async (index) => {
  if (currentRouteIndex.value === index) return
  
  currentRouteIndex.value = index
  ElMessage.info('正在计算路线详情...')
  
  // 清除现有路线
  clearRoutes()
  
  // 重新规划路线
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

// 计算路线
const calculateRoute = (routeData, routeType, routeIndex = currentRouteIndex.value) => {
  if (!driving.value || !routeData || !isMapReady.value) return
  
  console.log('开始规划路线:', { routeData, routeType, routeIndex })
  
  const { start_point, end_point, waypoints } = routeData
  
  // 清除已有路线
  driving.value.clear()
  map.value.clearMap()
  
  // 设置驾驶策略
  const policyMap = {
    'LEAST_TIME': AMap.DrivingPolicy.LEAST_TIME,
    'LEAST_FEE': AMap.DrivingPolicy.LEAST_FEE,
    'LEAST_DISTANCE': AMap.DrivingPolicy.LEAST_DISTANCE,
    'REAL_TRAFFIC': AMap.DrivingPolicy.REAL_TRAFFIC
  }
  
  const policy = policyMap[routeType] || AMap.DrivingPolicy.LEAST_TIME
  driving.value.setPolicy(policy)
  
  // 使用地理编码服务获取坐标
  const geocoder = new AMap.Geocoder({
    city: "全国"
  })
  
  // 获取起点坐标
  geocoder.getLocation(start_point, (status, result) => {
    if (status === 'complete' && result.geocodes.length) {
      const startLoc = result.geocodes[0].location
      
      // 获取终点坐标
      geocoder.getLocation(end_point, (status, result) => {
        if (status === 'complete' && result.geocodes.length) {
          const endLoc = result.geocodes[0].location
          
          // 获取途经点坐标
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
          
          // 等待所有经点坐标获取完成
          Promise.all(getWayPointPromises).then(wayPointLocs => {
            const validWayPoints = wayPointLocs.filter(loc => loc !== null)
            
            // 规划驾车导航路线
            driving.value.search(
              startLoc,
              endLoc,
              {
                waypoints: validWayPoints
              },
              (status, result) => {
                if (status === 'complete' && result.routes && result.routes.length) {
                  const route = result.routes[0]
                  
                  // 更新路线信息
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
                  
                  // 更新路线列表中的信息
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

// 监听路由化，清理地图
onBeforeUnmount(() => {
  if (map.value) {
    map.value.destroy()
    map.value = null
  }
  if (driving.value) {
    driving.value.clear()
    driving.value = null
  }

  // 移除页面刷新事件监听
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

// 切换折叠状态
const toggleRouteOptions = () => {
  showRouteOptions.value = !showRouteOptions.value
}

const toggleRouteSummary = () => {
  showRouteSummary.value = !showRouteSummary.value
}

// 切换路况图层
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

// 切换卫星图层
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

// 切换建筑物图层
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

// 切换3D效果
const toggle3D = (value) => {
  if (map.value) {
    map.value.setFeatures(value ? ['bg', 'building', 'point'] : ['bg', 'point'])
  }
}

// 处理快速操作
const handleQuickAction = async (action) => {
  try {
    // 构建请求参数
    const requestParams = {
      text: action.prompt
        .replace('{start}', '北京西站')
        .replace('{end}', '首都机场')
        .replace('{spots}', '郑州工程技术学院'),
      type: action.id
    }

    // 发送请求
    const response = await store.sendChatMessage(requestParams)
    
    if (response.success && response.route_data) {
      // 确保地图已初始化
      if (!isMapReady.value) {
        await initMap()
      }

      // 清除现有路线
      clearRoutes()

      // 处理路线数据
      const routeData = response.route_data
      
      // 获取推荐路线列表
      const recommendedRoutes = routeData.recommended_routes || []
      routes.value = recommendedRoutes.map(route => ({
        ...route,
        duration: 0,  // 初始化为0，后续更新
        distance: 0,
        toll: 0
      }))
      
      // 计算第一条路线
      if (routes.value.length > 0) {
        currentRouteIndex.value = 0
        await calculateRoute(routeData.route_info, routes.value[0].type)
        
        // 如果有第二条路线，也计算一下
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

// 处理建议选择
const handleSuggestion = (suggestion) => {
  console.log('Selected suggestion:', suggestion)
  // TODO: 实现建议选择逻辑
}

const guideSystem = ref(null)

const resetGuide = () => {
  guideSystem.value?.resetGuide()
}

// 添加城市名称转换函数
const getCityName = (adcode) => {
  const cityInfo = citiesData[adcode]
  return cityInfo ? cityInfo.name : adcode
}

// 修改路线数据处理函数
const handleRouteData = async (routeData) => {
  if (!driving.value) return
  
  // 清除现有路线
  clearRoutes()
  
  // 检查路线数据是否有效
  if (!routeData || !routeData.route_info) {
    console.error('无效的路线数据:', routeData)
    ElMessage.error('路线数据无效')
    return
  }
  
  console.log('接收到的路线数据:', routeData)
  
  // 初始化推荐路线信息
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
  ]

  const { start_point, end_point, waypoints = [] } = routeData.route_info
  
  try {
    // 使用地理编码服务获取坐标
    const geocoder = new AMap.Geocoder()
    
    // 获取起点坐标
    const startResult = await new Promise((resolve, reject) => {
      geocoder.getLocation(start_point, (status, result) => {
        if (status === 'complete' && result.geocodes.length) {
          resolve(result.geocodes[0].location)
        } else {
          reject(new Error('起点地址解析失败'))
        }
      })
    })
    
    // 获取终点坐标
    const endResult = await new Promise((resolve, reject) => {
      geocoder.getLocation(end_point, (status, result) => {
        if (status === 'complete' && result.geocodes.length) {
          resolve(result.geocodes[0].location)
        } else {
          reject(new Error('终点地址解析失败'))
        }
      })
    })
    
    // 获取途经点坐标
    const waypointPromises = waypoints.map(point =>
      new Promise((resolve, reject) => {
        if (!point) {
          resolve(null)
          return
        }
        geocoder.getLocation(point.toString(), (status, result) => {
          if (status === 'complete' && result.geocodes.length) {
            resolve(result.geocodes[0].location)
          } else {
            console.warn(`途经点 ${point} 地址解析失败`)
            resolve(null)
          }
        })
      })
    )
    
    const waypointResults = await Promise.all(waypointPromises)
    const validWaypoints = waypointResults.filter(Boolean)
    
    // 规划路线
    driving.value.search(
      startResult,
      endResult,
      {
        waypoints: validWaypoints,
        extensions: 'all'
      },
      (status, result) => {
        if (status === 'complete') {
          console.log('路线规划成功:', result)
          
          if (result.routes && result.routes[0]) {
            const polyline = new AMap.Polyline({
              path: result.routes[0].steps.map(step => step.path).flat(),
              strokeColor: "#00B96B",
              strokeWeight: 6,
              strokeOpacity: 0.8
            })
            
            map.value.add(polyline)
            currentRoutes.value.push(polyline)
            
            // 调整视图以显示整个路线
            map.value.setFitView()

            const route = result.routes[0]
            
            // 处理途经城市信息
            const citiesList = []
            if (route.steps) {
              route.steps.forEach(step => {
                if (step.city && !citiesList.includes(step.city)) {
                  const cityName = getCityName(step.city)
                  if (cityName) {
                    citiesList.push(cityName)
                  }
                }
              })
            }

            // 更新推荐路线信息
            const routeDetails = {
              duration: Math.round(route.time / 60),
              distance: (route.distance / 1000).toFixed(1),
              toll: route.tolls || 0
            }
            
            // 更新当前选中的路线信息
            routes.value[currentRouteIndex.value] = {
              ...routes.value[currentRouteIndex.value],
              ...routeDetails
            }
            
            // 如果是第一条路线，同时更新备选路线的预估信息
            if (currentRouteIndex.value === 0) {
              routes.value[1] = {
                ...routes.value[1],
                duration: Math.round(route.time * 1.2 / 60),
                distance: (route.distance * 1.1 / 1000).toFixed(1),
                toll: Math.max(0, (route.tolls || 0) * 0.8)
              }
            }

            // 更新路线详情信息
            routeInfo.value = {
              start_point: start_point,
              end_point: end_point,
              ...routeDetails,
              restriction: false,
              cities: citiesList.length > 0 ? citiesList.join(' → ') : '加载中...',
              waypoints: waypoints
            }
          }
          
          ElMessage.success('路线规划成功')
        } else {
          console.error('路线规划失败:', result)
          ElMessage.error('路线规划失败，请重试')
          // 重置路线信息
          routes.value = routes.value.map(route => ({
            ...route,
            duration: '--',
            distance: '--',
            toll: '--'
          }))
        }
      }
    )
  } catch (error) {
    console.error('地址解析失败:', error)
    ElMessage.error('地址解析失败，请重试')
    // 重置路线信息
    routes.value = routes.value.map(route => ({
      ...route,
      duration: '--',
      distance: '--',
      toll: '--'
    }))
  }
}

// 替换 loading 组件的使用方式
const showLoading = () => {
  return ElLoading.service({
    target: '.map-wrapper',
    text: '地图加载中...'
  })
}

// 创建新路线
const createNewRoute = () => {
  // 如果当前已经有路线，询问是否保存
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
      // 保存当前路线记录
      saveCurrentRoute().then(() => {
        resetRouteAndChat()
      })
    }).catch((action) => {
      // 如果是取消（不保存直接创建），则直接重置
      if (action === 'cancel') {
        resetRouteAndChat()
      }
      // 如果是关闭对话框，什么都不做
    })
  } else {
    // 如果没有当前路线，直接重置
    resetRouteAndChat()
  }
}

// 重置路线和聊天历史
const resetRouteAndChat = () => {
  // 清空聊天历史
  store.startNewRouteSession()
  
  // 清空地图和路线
  clearRoutes()
  
  // 重置路线信息
  routeInfo.value = null
  
  // 重置推荐路线
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

// 保存当前路线记录
const saveCurrentRoute = async () => {
  if (!routeInfo.value) return false
  
  // 保存路线记录
  const success = store.saveRouteRecord(routeInfo.value)
  
  if (success) {
    ElMessage.success('路线记录保存成功')
  } else {
    ElMessage.error('保存路线记录失败')
  }
  
  return success
}

// 加载选中的路线记录
const loadSelectedRouteRecord = () => {
  const record = store.loadSelectedRouteRecord()
  if (!record) return false
  
  // 加载路线数据
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

// 用于处理页面刷新时保存路线记录
const handleBeforeUnload = (e) => {
  console.log("检测到页面刷新，保存并创建新路线");
  // 如果有有效路线，则自动保存
  if (map.value && currentRoute.value && currentRoute.value.path && 
      startPoint.value && endPoint.value) {
    try {
      // 构建路线信息对象
      const routeInfo = {
        start_point: startPoint.value.text || '',
        end_point: endPoint.value.text || '',
        waypoints: waypoints.value.map(wp => wp.text || ''),
        distance: currentRoute.value.distance,
        duration: currentRoute.value.time,
        toll: currentRoute.value.toll,
        type: currentRoute.value.routeType || 'DEFAULT',
        path: currentRoute.value.path
      };
      
      // 验证路线信息对象
      if (!routeInfo.start_point || !routeInfo.end_point) {
        console.warn('路线起点或终点无效，不保存');
        return;
      }
      
      // 保存到store
      store.saveRouteRecord(routeInfo);
    } catch (err) {
      console.error('自动保存路线失败:', err);
    }
  }
};

// 注册页面刷新事件，确保用户刷新页面时保存路线
onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
})

// 在离开页面前自动保存路线记录
onBeforeUnmount(() => {
  // 只有当有路线信息时才尝试保存
  if (routeInfo.value) {
    saveCurrentRoute()
  }
  
  // 移除页面刷新事件监听
  window.removeEventListener('beforeunload', handleBeforeUnload)
  
  // 清理地图
  if (map.value) {
    map.value.destroy()
    map.value = null
  }
  if (driving.value) {
    driving.value.clear()
    driving.value = null
  }
})

// 在页面激活时恢复路线规划状态
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
  background: var(--el-bg-color);
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
}

.route-info-container {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  max-height: calc(100vh - 340px);
  box-shadow: var(--el-box-shadow-light);
}

.map-wrapper {
  position: relative;
  flex: 1;
  min-height: 400px;
  height: calc(100vh - 100px);
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
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

/* 动画效果 */
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
  max-height: 2000px; /* 增加最大高度，确保内容能完全显示 */
  opacity: 1;
  overflow: hidden;
}

.route-options.is-collapsed,
.route-details.is-collapsed {
  max-height: 0;
  opacity: 0;
  margin: 0;
  padding: 0;
}

/* 确保卡片内容区域有过渡效果 */
.el-card__body {
  transition: padding 0.3s ease-in-out;
}

.el-card__body:has(.is-collapsed) {
  padding: 0;
}

/* 添加内容区域的基础样式 */
.route-options,
.route-details {
  padding: 20px;
}

.route-options.is-collapsed,
.route-details.is-collapsed {
  padding: 0;
}

.reset-guide-btn {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
}

/* 确保地图控件样式正确 */
:deep(.amap-logo) {
  opacity: 8;
}

:deep(.amap-copyright) {
  opacity: 0.8;
}

/* 自定义滚动条样式 */
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

/* 优化路线详情面板样式 */
:deep(#panel) {
  padding: 16px;
  background: transparent !important;
}

:deep(#panel .amap-lib-driving) {
  border-radius: 8px;
  background: var(--el-bg-color) !important;
}

:deep(#panel .amap-lib-driving .planTitle) {
  background: var(--el-color-primary-light-9) !important;
  border-bottom: 1px solid var(--el-border-color-lighter) ;
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

/* 添加新建路线按钮的样式 */
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
</style>
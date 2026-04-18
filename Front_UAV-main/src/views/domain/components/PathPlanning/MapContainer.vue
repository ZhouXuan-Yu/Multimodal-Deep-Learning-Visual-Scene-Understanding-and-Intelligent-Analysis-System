// -*- coding: utf-8 -*-
<template>
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
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import config from '../../api/config'

// 确保中文文本正确显示
const UTF8 = true;  // 启用UTF-8编码支持

const props = defineProps({
  routeInfo: {
    type: Object,
    default: () => null
  },
  currentRouteIndex: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['route-calculated'])

// 地图实例
const map = ref(null)
const driving = ref(null)
const isMapReady = ref(false)
const currentRoutes = ref([])

// 图层控制
const showTraffic = ref(false)
const showSatellite = ref(false)
const showBuildings = ref(true)

// 确保AMap可用 
const checkAMapLoaded = () => {
  return new Promise((resolve, reject) => {
    // 已加载则直接返回
    if (window.AMap) {
      resolve(window.AMap);
      return;
    }
    
    // 否则打印错误并拒绝承诺
    const error = new Error('高德地图API尚未加载，请检查网络连接或API密钥是否正确');
    console.error(error);
    reject(error);
  });
};

// 初始化高德地图
const initMap = async () => {
  try {
    console.log('正在初始化地图...')
    
    // 确保AMap已加载
    await checkAMapLoaded();
    
    console.log('AMap已加载，创建地图实例...')
    
    // 清理可能存在的旧地图实例
    if (map.value) {
      try {
        map.value.destroy();
      } catch (e) {
        console.warn('清理旧地图实例失败:', e);
      }
      map.value = null;
    }
    
    // 确保容器存在且尺寸合适
    const container = document.getElementById('container');
    if (!container) {
      throw new Error('地图容器元素不存在!');
    }
    
    const rect = container.getBoundingClientRect();
    console.log('地图容器尺寸:', rect);
    
    if (rect.width < 10 || rect.height < 10) {
      console.warn('地图容器尺寸异常，尝试修复...');
      container.style.width = '100%';
      container.style.height = '600px';
    }
    
    // 创建地图实例，设置默认中心点为北京
    map.value = new AMap.Map('container', {
      zoom: 12,
      center: [116.397428, 39.90923], // 默认中心点：北京
      viewMode: '3D',
      // 添加willReadFrequently属性以优化Canvas2D性能
      canvas: {
        willReadFrequently: true
      },
      // 确保地图支持3D效果
      features: ['bg', 'building', 'point'],
      // 强制启用WebGL模式
      renderer: 'webgl',
      // 确保容器正确显示
      resizeEnable: true
    })
    
    // 添加事件监听器，以确认地图已完全加载
    map.value.on('complete', () => {
      console.log('地图加载完成')
      isMapReady.value = true
    })
    
    // 创建驾车导航实例
    console.log('创建驾车导航实例...')
    driving.value = new AMap.Driving({
      map: map.value,
      panel: 'panel',
      autoFitView: true,
      showTraffic: false // 默认不显示路况
    })
    
    // 验证地图实例是否有效
    if (!map.value || typeof map.value.getCenter !== 'function') {
      throw new Error('地图实例创建失败或无效');
    }
    
    // 添加缩放控件
    map.value.addControl(new AMap.Scale());
    map.value.addControl(new AMap.ToolBar());
    
    // 强制刷新地图大小 - 延迟执行以确保DOM已更新
    setTimeout(() => {
      console.log('强制调整地图大小...')
      if (map.value) {
        map.value.resize();
      }
    }, 200);
    
    // 再次检查地图实例
    setTimeout(() => {
      if (map.value && typeof map.value.getCenter === 'function') {
        console.log('地图中心点:', map.value.getCenter());
        
        // 尝试重新绘制一些内容以激活地图
        const marker = new AMap.Marker({
          position: map.value.getCenter()
        });
        map.value.add(marker);
        setTimeout(() => map.value.remove(marker), 100);
      } else {
        console.error('地图实例检查失败');
      }
    }, 500);
    
    console.log('地图初始化成功')
    isMapReady.value = true
  } catch (error) {
    console.error('地图初始化失败:', error)
    ElMessage.error('地图初始化失败，请刷新页面重试')
    throw error
  }
}

// 清除已有路线
const clearRoutes = () => {
  if (driving.value) {
    driving.value.clear()
  }
  currentRoutes.value.forEach(route => {
    map.value?.remove(route)
  })
  currentRoutes.value = []
}

// 计算路线
const calculateRoute = async (routeData, routeType) => {
  console.log('[MapContainer] 开始计算路线, 输入数据:', { 
    routeData: JSON.parse(JSON.stringify(routeData)), 
    routeType,
    drivingInstance: !!driving.value,
    isMapReady: isMapReady.value
  })
  
  // 强制刷新地图容器大小，解决可能的渲染问题
  setTimeout(() => {
    if (map.value) {
      console.log('[MapContainer] 强制刷新地图大小');
      map.value.resize();
    }
  }, 0);
  
  // 检查地图容器是否正确加载
  const containerElement = document.getElementById('container')
  if (!containerElement) {
    console.error('[MapContainer] 地图容器元素不存在!')
    ElMessage.error('地图容器未找到，请刷新页面重试')
    return
  }

  // 检查高德地图API是否加载
  if (!window.AMap) {
    console.error('[MapContainer] 高德地图API未加载!');
    ElMessage.error('地图API未加载，请刷新页面');
    return;
  }
  
  // 检查容器尺寸
  const containerRect = containerElement.getBoundingClientRect()
  console.log('[MapContainer] 地图容器尺寸:', {
    width: containerRect.width,
    height: containerRect.height
  })
  
  // 如果容器尺寸太小，可能导致地图不显示
  if (containerRect.width < 10 || containerRect.height < 10) {
    console.error('[MapContainer] 地图容器尺寸异常!')
    ElMessage.error('地图容器尺寸异常，请检查样式设置')
    
    // 尝试修复容器尺寸
    containerElement.style.width = '100%'
    containerElement.style.height = '100%'
    
    // 延迟后重新初始化地图
    setTimeout(async () => {
      if (map.value) {
        map.value.destroy()
        map.value = null
      }
      
      try {
        await initMap()
        // 重新尝试路线计算
        calculateRoute(routeData, routeType)
      } catch (error) {
        console.error('[MapContainer] 地图重新初始化失败:', error)
      }
    }, 500)
    return
  }
  
  // 检查各种必要条件
  if (!driving.value) {
    console.error('[MapContainer] 驾车导航实例未创建')
    ElMessage.error('驾车导航功能未初始化')
    return
  }
  
  if (!routeData) {
    console.error('[MapContainer] 路线数据为空')
    ElMessage.error('路线数据为空，无法规划路线')
    return
  }
  
  if (!isMapReady.value) {
    console.error('[MapContainer] 地图尚未就绪')
    ElMessage.error('地图尚未就绪，请稍后再试')
    return
  }
  
  console.log('[MapContainer] 开始规划路线:', { routeData, routeType })
  
  const { start_point, end_point, waypoints = [] } = routeData
  
  if (!start_point || !end_point) {
    console.error('起点或终点为空:', { start_point, end_point })
    ElMessage.error('起点或终点未指定')
    return
  }
  
  // 清除已有路线
  clearRoutes()
  
  // 设置驾驶策略
  const policyMap = {
    'fastest': AMap.DrivingPolicy.LEAST_TIME,
    'economic': AMap.DrivingPolicy.LEAST_FEE,
    'LEAST_TIME': AMap.DrivingPolicy.LEAST_TIME,
    'LEAST_FEE': AMap.DrivingPolicy.LEAST_FEE,
    'LEAST_DISTANCE': AMap.DrivingPolicy.LEAST_DISTANCE,
    'REAL_TRAFFIC': AMap.DrivingPolicy.REAL_TRAFFIC
  }
  
  const policy = policyMap[routeType] || AMap.DrivingPolicy.LEAST_TIME
  console.log(`设置驾驶策略: ${routeType} => ${Object.keys(AMap.DrivingPolicy).find(key => AMap.DrivingPolicy[key] === policy) || policy}`)
  driving.value.setPolicy(policy)
  
  // 创建一个变量来跟踪是否已经关闭loading
  let loadingClosed = false;

  try {
    // 显示加载状态
    const loading = ElLoading.service({
      target: '.map-container',
      text: '正在规划路线...'
    });

    // 设置安全超时，确保loading在5秒后强制关闭
    const safetyTimeout = setTimeout(() => {
      if (!loadingClosed) {
        console.warn('[MapContainer] 强制关闭loading (安全超时)');
        try {
          loading.close();
        } catch (e) {
          console.error('关闭loading失败:', e);
        }
        
        // 尝试移除所有loading遮罩
        document.querySelectorAll('.el-loading-mask').forEach(el => el.remove());
        loadingClosed = true;
      }
    }, 5000);
    
    console.log('[MapContainer] 使用关键字搜索直接规划路线:',
                { start: start_point, end: end_point, waypoints: waypoints });
    
    // 直接使用关键字搜索方式规划路线，跳过地理编码步骤
    driving.value.search(
      [{ keyword: start_point, city: '全国' }],
      [{ keyword: end_point, city: '全国' }],
      {
        waypoints: waypoints.map(point => ({ keyword: point, city: '全国' }))
      },
      (status, result) => {
        // 关闭loading
        if (!loadingClosed) {
          try {
            loading.close();
          } catch (e) {
            console.warn('关闭loading失败:', e);
          }
          
          // 尝试移除所有loading遮罩
          document.querySelectorAll('.el-loading-mask').forEach(el => el.remove());
          loadingClosed = true;
          
          // 清除安全超时
          clearTimeout(safetyTimeout);
        }
        
        console.log('[MapContainer] 路线规划回调状态:', status);
        console.log('[MapContainer] 回调结果类型:', result ? typeof result : 'undefined');
        
        if (status === 'complete' && result && result.routes && result.routes.length) {
          console.log('[MapContainer] 路线规划成功');
          
          const route = result.routes[0];
          
          // 在地图上添加起点标记
          if (result.start && result.start.location) {
            const startMarker = new AMap.Marker({
              position: result.start.location,
              title: start_point,
              icon: 'https://webapi.amap.com/theme/v1.3/markers/n/start.png'
            });
            map.value.add(startMarker);
            currentRoutes.value.push(startMarker);
          }
          
          // 在地图上添加终点标记
          if (result.end && result.end.location) {
            const endMarker = new AMap.Marker({
              position: result.end.location,
              title: end_point,
              icon: 'https://webapi.amap.com/theme/v1.3/markers/n/end.png'
            });
            map.value.add(endMarker);
            currentRoutes.value.push(endMarker);
          }
          
          // 在地图上添加途经点标记
          if (result.waypoints && result.waypoints.length) {
            result.waypoints.forEach((waypoint, index) => {
              if (waypoint && waypoint.location) {
                const waypointMarker = new AMap.Marker({
                  position: waypoint.location,
                  title: `途经点${index+1}: ${waypoints[index] || ''}`,
                  icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mid.png'
                });
                map.value.add(waypointMarker);
                currentRoutes.value.push(waypointMarker);
              }
            });
          }
          
          try {
            // 创建并添加路线折线
            const polyline = new AMap.Polyline({
              path: route.steps.map(step => step.path).flat(),
              strokeColor: "#00B96B",
              strokeWeight: 6,
              strokeOpacity: 0.8,
              strokeStyle: "solid",
              lineJoin: "round"
            });
            
            map.value.add(polyline);
            currentRoutes.value.push(polyline);
            
            // 调整视图以显示整个路线和所有标记点
            map.value.setFitView(currentRoutes.value);
            
            // 获取途经城市信息
            const uniqueCities = new Set();
            if (route.steps) {
              route.steps.forEach(step => {
                if (step.city) {
                  uniqueCities.add(step.city);
                }
              });
            }
            const citiesList = Array.from(uniqueCities);
            
            // 构建路线返回数据
            const routeResultData = {
              ...routeData,
              distance: (route.distance / 1000).toFixed(1),  // 转换为千米
              duration: Math.ceil(route.time / 60),  // 转换为分钟
              toll: route.tolls || 0,
              restriction: route.restriction ? '有限行' : '无限行',
              cities: citiesList.join(' → ')
            };
            
            // 向父组件发送计算结果
            emit('route-calculated', routeResultData);
            
            console.log('[MapContainer] 路线计算完成，结果:', routeResultData);
          } catch (error) {
            console.error('[MapContainer] 处理路线数据时出错:', error);
            ElMessage.error('处理路线数据时出错: ' + error.message);
          }
        } else {
          console.error('[MapContainer] 路线规划失败:', status, result ? result.info : 'No result');
          
          // 尝试不带城市限制的搜索作为后备方案
          console.log('[MapContainer] 尝试使用不带城市限制的搜索');
          
          driving.value.search(
            start_point, 
            end_point, 
            { waypoints: waypoints }, 
            (retryStatus, retryResult) => {
              console.log('[MapContainer] 重试搜索状态:', retryStatus);
              
              if (retryStatus === 'complete' && retryResult && retryResult.routes && retryResult.routes.length) {
                console.log('[MapContainer] 重试搜索成功');
                
                const route = retryResult.routes[0];
                
                try {
                  // 创建并添加路线折线
                  const polyline = new AMap.Polyline({
                    path: route.steps.map(step => step.path).flat(),
                    strokeColor: "#00B96B",
                    strokeWeight: 6,
                    strokeOpacity: 0.8,
                    strokeStyle: "solid",
                    lineJoin: "round"
                  });
                  
                  map.value.add(polyline);
                  currentRoutes.value.push(polyline);
                  
                  // 调整视图以显示整个路线
                  map.value.setFitView(currentRoutes.value);
                  
                  // 获取途经城市信息
                  const uniqueCities = new Set();
                  if (route.steps) {
                    route.steps.forEach(step => {
                      if (step.city) {
                        uniqueCities.add(step.city);
                      }
                    });
                  }
                  const citiesList = Array.from(uniqueCities);
                  
                  // 构建路线返回数据
                  const routeResultData = {
                    ...routeData,
                    distance: (route.distance / 1000).toFixed(1),
                    duration: Math.ceil(route.time / 60),
                    toll: route.tolls || 0,
                    restriction: route.restriction ? '有限行' : '无限行',
                    cities: citiesList.join(' → ')
                  };
                  
                  // 向父组件发送计算结果
                  emit('route-calculated', routeResultData);
                  
                  console.log('[MapContainer] 重试路线计算完成，结果:', routeResultData);
                } catch (error) {
                  console.error('[MapContainer] 处理重试路线数据时出错:', error);
                  ElMessage.error('处理路线数据时出错: ' + error.message);
                }
              } else {
                // 显示友好的错误提示
                ElMessage({
                  message: `无法规划路线: ${retryResult?.info || '请尝试更精确的地点描述'}`,
                  type: 'error',
                  duration: 5000
                });
              }
            }
          );
        }
      }
    );
  } catch (error) {
    console.error('[MapContainer] 路线计算过程中出错:', error);
    
    // 确保loading已关闭
    if (!loadingClosed) {
      // 尝试关闭可能存在的loading
      document.querySelectorAll('.el-loading-mask').forEach(el => el.remove());
      loadingClosed = true;
    }
    
    // 显示错误提示
    ElMessage.error('路线计算失败: ' + error.message);
  }
}

// 切换交通状况图层
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

// 监听路线信息变化
watch(() => props.routeInfo, (newRouteInfo, oldRouteInfo) => {
  console.log('[MapContainer] 路线信息变化:', 
    { 
      new: newRouteInfo ? JSON.parse(JSON.stringify(newRouteInfo)) : null,
      old: oldRouteInfo ? JSON.parse(JSON.stringify(oldRouteInfo)) : null
    }
  )
  
  if (newRouteInfo && isMapReady.value) {
    console.log('[MapContainer] 路线信息就绪，将调用计算路线')
    
    // 确保地图容器尺寸正确
    const containerElement = document.getElementById('container')
    if (containerElement) {
      const rect = containerElement.getBoundingClientRect()
      if (rect.width < 10 || rect.height < 10) {
        console.warn('[MapContainer] 地图容器尺寸异常，尝试修复...')
        containerElement.style.width = '100%'
        containerElement.style.height = '400px'
        
        // 延迟后重新调整地图并计算路线
        setTimeout(() => {
          if (map.value) {
            map.value.resize()
          }
          calculateRoute(newRouteInfo, 'LEAST_TIME')
        }, 500)
        return
      }
    }
    
    calculateRoute(newRouteInfo, 'LEAST_TIME')
  } else {
    console.log('[MapContainer] 路线信息变化但条件不满足:',
      { hasRouteInfo: !!newRouteInfo, isMapReady: isMapReady.value })
  }
}, { deep: true })

// 初始化地图
onMounted(async () => {
  console.log('[MapContainer] 组件挂载，准备初始化地图...')
  console.log('[MapContainer] 检查DOM元素:', { 
    mapWrapper: !!document.querySelector('.map-wrapper'),
    mapContainer: !!document.getElementById('container')
  })
  
  // 先设定一个合理的尺寸
  const containerElement = document.getElementById('container');
  if (containerElement) {
    containerElement.style.width = '100%';
    containerElement.style.height = '500px';
  }
  
  const loading = ElLoading.service({
    target: '.map-wrapper',
    text: '地图加载中...'
  })
  
  try {
    // 等待高德地图API加载完成
    if (!window.AMap) {
      console.log('[MapContainer] 等待高德地图API加载...');
      
      // 等待最多8秒
      for (let i = 0; i < 8; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        if (window.AMap) {
          console.log(`[MapContainer] 高德地图API已加载 (等待了${i+1}秒)`);
          break;
        }
        console.log(`[MapContainer] 等待高德地图API加载中... (${i+1}秒)`);
      }
      
      if (!window.AMap) {
        throw new Error('高德地图API加载超时');
      }
    }
    
    await initMap()
    loading.close()
    console.log('[MapContainer] 地图初始化完成')
    
    // 延迟处理，确保DOM已完全渲染
    setTimeout(() => {
      // 再次检查和调整地图容器尺寸
      const container = document.getElementById('container');
      if (container) {
        const rect = container.getBoundingClientRect();
        console.log('[MapContainer] 初始化后地图容器尺寸:', rect);
        
        if (rect.width < 100 || rect.height < 100) {
          console.warn('[MapContainer] 地图容器尺寸仍然异常，进行二次修复');
          container.style.width = '100%';
          container.style.height = '500px';
          
          // 重新调整地图
          if (map.value) {
            map.value.resize();
          }
        }
      }
      
      // 如果已有路线信息，立即规划路线
      if (props.routeInfo) {
        console.log('[MapContainer] 挂载时检测到路线信息，立即规划路线', props.routeInfo)
        calculateRoute(props.routeInfo, 'LEAST_TIME')
      } else {
        console.log('[MapContainer] 挂载时没有检测到路线信息')
        
        // 无路线信息时，确保地图显示正常
        if (map.value) {
          map.value.resize();
          map.value.setZoom(12);
          map.value.setCenter([116.397428, 39.90923]); // 默认中心点：北京
        }
      }
    }, 500);
    
    // 添加窗口大小变化监听，确保地图自适应调整
    const handleResize = () => {
      if (map.value) {
        console.log('[MapContainer] 窗口大小变化，调整地图大小');
        map.value.resize();
      }
    };
    
    window.addEventListener('resize', handleResize);
    
    // 组件卸载时移除监听
    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize);
    });
    
  } catch (error) {
    console.error('[MapContainer] 地图初始化失败:', error)
    loading.close()
    
    // 显示友好的错误信息
    ElMessage({
      message: `地图初始化失败: ${error.message || '请刷新页面重试'}`,
      type: 'error',
      duration: 0 // 不自动关闭
    });
  }
})

// 销毁当前的资源
onBeforeUnmount(() => {
  if (map.value) {
    map.value.destroy()
    map.value = null
  }
  if (driving.value) {
    driving.value.clear()
    driving.value = null
  }
})

// 暴露方法给父组件
defineExpose({
  calculateRoute,
  clearRoutes
})
</script>

<style scoped>
.map-wrapper {
  position: relative;
  flex: 1;
  min-height: 400px;
  height: calc(100vh - 100px);
  border-radius: 8px;
  overflow: hidden;
  z-index: 1; /* 确保地图层级正确 */
  display: flex; /* 确保子元素能撑满 */
}

.map-container {
  width: 100% !important;
  height: 100% !important;
  min-height: 400px; /* 确保最小高度 */
  background: var(--el-bg-color-overlay);
  flex: 1; /* 确保撑满父容器 */
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

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
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
</style>
- 修改加入途径点
    方法

返回值

说明

search(origin:LngLat,destination:LngLat,opts:Object,

callback:function(status:String,result:info/DrivingResult))

或 search(points:Array.<Object>,

callback:function(status:String,result:info/DrivingResult))



根据起点、终点和途经点（可选）坐标或名称，实现驾车路线规划，途经点通过opts设定，最多支持16个途径点，opts:{waypoints:Array.<LngLat>}；

status为complete时，result为DrivingResult；

当status为error时，result为错误信息info；

当status为no_data时，代表检索返回0结果。

注：以名称关键字查询时，points为起点、终点和途经点（可选）名称及对应城市的数组，例如：

[{keyword:‘北京南站’,city:‘北京市’},

{keyword:‘广东大厦’,city:’北京市’},

{ keyword:‘北京西站’,city:‘北京市’}]

系统取数组第一个元素和最后一个元素作为起点和终点，中间元素为途经点；



 起终点为经纬度，请使用search(origin:LngLat,destination:LngLat,opts:Object,
callback:function(status:String,result:info/DrivingResult))

起终点为字符串（汉字，比如北京，重庆），请使用search(points:Array.<Object>,
callback:function(status:String,result:info/DrivingResult)) 

setPolicy(policy:DrivingPolicy)



设置驾车路线规划策略，可选值：LEAST_TIME（最短时间）、LEAST_DISTANCE（最短距离）、LEAST_FEE（最少费用）、AVOID_HIGHWAYS（避开高速）。根据本地大模型和算法根据用户语境自动选择最优策略，无需设置。然后找到最适合的两条路线为推荐路线和备用路线。


- 补充信息
驾车策略 
DrivingPolicy

类型

说明

AMap.DrivingPolicy.LEAST_TIME

Const

最快捷模式

AMap.DrivingPolicy.LEAST_FEE

Const

最经济模式

AMap.DrivingPolicy.LEAST_DISTANCE

Const

最短距离模式

AMap.DrivingPolicy.REAL_TRAFFIC

Const

考虑实时路况

DrivingResult 对象
属性

类型

说明

info

String

成功状态说明

origin

LngLat

驾车规划起点坐标

destination

LngLat

驾车规划终点坐标

start

Poi

驾车规划起点

end

Poi

驾车规划终点

waypoints

Poi

驾车规划途经点

taxi_cost

Number

打车费用，仅extensions为“all”时返回

单位：元

routes

Array.<DriveRoute>

驾车规划路线列表

DriveRoute 对象
属性

类型

说明

distance

Number

起点到终点的驾车距离，单位：米

time

Number

时间预计，单位：秒

policy

String

驾车规划策略

tolls

Number

此驾车路线收费金额，单位：元

tolls_distance

Number

收费路段长度，单位：米

steps

Array.<DriveStep>

子路段DriveStep集合

 restriction 

Number

限行结果

0 代表限行已规避或未限行，即该路线没有限行路段

1 代表限行无法规避，即该线路有限行路段

DriveStep 对象(基本信息)
属性

类型

说明

start_location

LngLat

此路段起点

end_location

LngLat

此路段终点

instruction

String

此路段说明，如“沿北京南站路行驶565米右转”

action

String

本驾车子路段完成后动作

assist_action

String

驾车子路段完成后辅助动作，一般为到达某个目的地时返回

orientation

String

驾车方向

road

String

道路

distance

Number

此路段距离，单位：米

tolls

Number

此段收费，单位：元

tolls_distance

Number

收费路段长度，单位：米

toll_road

String

主要收费道路

time

Number

此路段预计使用时间，单位：秒

path

Array.<LngLat>

此路段坐标集合

DriveStep 对象(详细信息）
属性

类型

说明

cities

Array.<ViaCity>

途径城市列表

tmcs

Array.<TMC>

实时交通信息列表

ViaCity 对象
属性

类型

说明

name

String

途径名称

citycode

String

城市编码

adcode

String

区域编码

districts

Array.<District>

途径行政区列表

District 对象
属性

类型

说明

name

String

区域名称

adcode

String

区域编码

TMC 对象
属性

类型

说明

lcode

String

路况信息对应的编码

如果direction是正向 lcode返回值大于0；否则lcode，返回值小于0；

如果返回0则说明此路段无lcode

distance

Number

此lcode对应的路段长度，单位: 米

status

String

路况状态，可能的值有：未知，畅通，缓行，拥堵
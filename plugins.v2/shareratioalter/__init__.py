
from multiprocessing import process
from typing import List, Tuple, Dict, Any, Optional


from app.db.site_oper import SiteOper
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.core.event import eventmanager, Event
from app.db.models.siteuserdata import SiteUserData
from app.schemas import Notification, NotificationType, MessageChannel

class ShareRatioAlter(_PluginBase):
    # 插件名称
    plugin_name = "站点分享率监控"
    # 插件描述
    plugin_desc = "监测站点分享率，低于自定义值时发送通知"
    # 插件图标
    plugin_icon = "world.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "velor2012"
    # 作者主页
    author_url = "https://github.com/velor2012"
    # 插件配置项ID前缀
    plugin_config_prefix = "ShareRatioAlter"
    # 加载顺序
    plugin_order = 21
    # 可使用的用户级别
    auth_level = 2
    site_oper = None
    # 日志前缀
    LOG_TAG = "[ShareRatioAlter]"

    # 站点选项
    site_options = []
    sites_config = {}
    # # 退出事件
    # _event = threading.Event()
    # 私有属性
    _enabled = False
    _onlyonce: bool = False
    
    def init_plugin(self, config: dict = None):
        self.site_oper = SiteOper()
        logger.info('1', SiteOper)
        # 站点选项
        self.site_options = self.__get_site_options()
        # self.active_sites = self.__get_enable_site_ids()
        
        # 读取配置
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            logger.info('2', config)
            self.sites_config = {}
            for site in self.site_options:
                logger.info('3', site)
                if f"{site['name']}_enabled" in config:
                    logger.info(site['name'])
                    self.sites_config[site['name']] = {
                        "enabled": config.get(f"{site['name']}_enabled", False),
                        "ratio": float(config.get(f"{site['name']}_ratio", -1)),
                    }
        if self._onlyonce:
            config["onlyonce"] = False
            self.check_sites_and_send()
            
            
        logger.info(f"插件原始配置: config: {config}")
        logger.info(f"插件配置 sites_config: {self.sites_config}")
    @eventmanager.register(EventType.SiteRefreshed)
    def send_msg(self, event: Event):
        """
        站点数据刷新事件时发送消息
        """
        logger.info(f"{self.LOG_TAG} 站点数据刷新,  event.event_data : ",  event.event_data )

        if event.event_data.get('site_id') != "*":
            return
        self.check_sites_and_send()

    def check_sites_and_send(self):
        """
        检查站点是否需要发送通知
        """
        # 消息内容
        messages = []
        # 获取站点数据
        res = self.__get_data()
        logger.info(f"{self.LOG_TAG} 站点数据: {res}")
        # 获取每个站点的分享率
        for data in res:
            if data['ratio'] < 0:
                continue
            target_ratio = self.sites_config[data['name']]['ratio']
            logger.info(f"{self.LOG_TAG} 站点分享率: {data['name']} 分享率: {data['ratio']} 设置阈值为： {target_ratio}")
            if target_ratio > 0 and data['ratio'] < target_ratio:
                # 发送通知
                logger.info(f"{self.LOG_TAG} 发送通知: {data['name']} 分享率: {data['ratio']} 设置阈值为： {target_ratio}")
                messages.append(f"{data['name']} 分享率 【过低！！ \n" + 
                            f"分享率: {data['ratio']} 设置阈值为： {target_ratio}\n" +
                            f"————————————")
        if len(messages) > 0:
            # 发送通知
            self.post_message(mtype=NotificationType.SiteMessage,
                                title="站点分享率过低告警", text="\n".join(messages))
    def __get_data(self) -> Tuple[str, List[SiteUserData], List[SiteUserData]]:
        """
        获取每个站点的分享率，并返回
        """
        # 获取所有原始数据
        raw_data_list: List[SiteUserData] = self.site_oper.get_userdata()
        # 每个站点只获取最近一条数据
        sorted_data_list = sorted(raw_data_list, key=lambda x: x.updated_day, reverse=False)
        processed_data_list = list(
            {
                f"{data.name}":
                {
                    "name": data.name,
                    "ratio": round(data.ratio, 2)
                } for data in sorted_data_list
            }.values())
        res = []
        for data in processed_data_list:
            if data['name'] in self.sites_config.keys() and self.sites_config[data['name']]['enabled']:
                res.append({
                    "name": data['name'],
                    "ratio": data['ratio']
                })
            else:
                data['ratio'] = -1
            
        # 排序
        res.sort(key=lambda x: x['ratio'], reverse=True)
        return res
        

    def post_message(self, channel: MessageChannel = None, mtype: NotificationType = None, title: Optional[str] = None,
                     text: Optional[str] = None, image: Optional[str] = None, link: Optional[str] = None,
                     userid: Optional[str] = None, username: Optional[str] = None,
                     **kwargs):
        """
        发送消息
        """
        if not link:
            link = settings.MP_DOMAIN(f"#/plugins?tab=installed&id={self.__class__.__name__}")
        self.chain.post_message(Notification(
            channel=channel, mtype=mtype, title=title, text=text,
            image=image, link=link, userid=userid, username=username, **kwargs
        ))

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        self.site_options = self.__get_site_options()
        site_options = self.site_options
        # 构建下载器配置表单
        all_site_options_forms =  []    
        for site in site_options:
            all_site_options_forms.append({
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {
                                'cols': 6
                            },
                            'content': [
                                {
                                    'component': 'VTextField',
                                    'props': {
                                        'model': f"{site['name']}_ratio",
                                        'label': f"{site['name']}",
                                        'type': 'number',
                                        'hint': '当分享率低于此值时发送通知'
                                    }
                                }
                            ]
                    },
                    {
                        'component': 'VCol',
                        'props': {
                                'cols': 4
                            },
                            'content': [
                                {
                                    'component': 'VSwitch',
                                    'props': {
                                        'model': f"{site['name']}_enabled",
                                        'label': '启用'
                                    }   
                                }
                            ]
                    }
                ]
            })
        
        logger.info(f"插件配置表单: {all_site_options_forms}")
        logger.info({**{f"{site['name']}_enabled": False for site in site_options}})

        return [
            {
                'component': 'VRow',
                    'content': [
                        {
                            'component': 'VCol',
                            'props': {
                                'cols': 12,
                                # 'md': 6
                            },
                            'content': [
                                {
                                    'component': 'VSwitch',
                                    'props': {
                                        'model': 'enabled',
                                        'label': '启用插件',
                                    }
                                }
                            ]
                        },
                        {
                            'component': 'VCol',
                            'props': {
                                'cols': 12,
                                'md': 4
                            },
                            'content': [
                                {
                                    'component': 'VSwitch',
                                    'props': {
                                        'model': 'onlyonce',
                                        'label': '立即运行一次',
                                    }
                                }
                            ]
                        }
                    ]
            },
            *all_site_options_forms
        ], {
            "enabled": False,
            "onlyonce": False,
            # 初始化下载器自定义标签配置
            **{f"{site['name']}_enabled": False for site in site_options}
        }


    def __get_site_options(self) -> List[Dict[str, Any]]:
        """
        获取站点选项
        """
        sites = self.site_oper.list_order_by_pri()
        if not sites:
            return []
        return [{
            'name': site.name,
            'id': site.id
        } for site in sites if site and site.is_active]

    # def __get_enable_site_ids(self) -> List[int]:
    #     """
    #     获取启用的站点IDs
    #     """
    #     sites = self.site_oper.list_order_by_pri()
    #     if not sites:
    #         return []
    #     return [site.id for site in sites if site and site.is_active]


    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        定义远程控制命令
        :return: 命令关键字、事件、描述、附带数据
        """
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        """
        pass


    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        try:
            logger.info('尝试停止插件服务...')
            logger.info('插件服务停止完成')
        except Exception as e:
            logger.error(f"插件服务停止异常: {str(e)}", exc_info=True)
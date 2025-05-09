
import threading
from typing import List, Tuple, Dict, Any

from app.helper.downloader import DownloaderHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.core.event import eventmanager, Event

class DownloaderTagAdder(_PluginBase):
    # 插件名称
    plugin_name = "下载器添加标签"
    # 插件描述
    plugin_desc = "给qb、tr的下载器贴标签（下载时触发）"
    # 插件图标
    plugin_icon = "world.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "velor2012"
    # 作者主页
    author_url = "https://github.com/velor2012"
    # 插件配置项ID前缀
    plugin_config_prefix = "Downloader_Tag_Adder"
    # 加载顺序
    plugin_order = 21
    # 可使用的用户级别
    auth_level = 2
    # 日志前缀
    LOG_TAG = "[DownloaderTagAdder]"

    # 退出事件
    _event = threading.Event()
    # 私有属性
    downloader_helper = None
    _scheduler = None
    _enabled = False
    _downloaders = None
    _downloader_configs = {}  # 下载器独立配置，存储自定义标签

    def init_plugin(self, config: dict = None):
        self.downloader_helper = DownloaderHelper()
        logger.info(f"{self.LOG_TAG} 初始化 ...")
        # 读取配置
        if config:
            self._enabled = config.get("enabled")
            self._downloaders = config.get("downloaders")
            # 读取下载器自定义标签配置
            self._downloader_configs = {}
            for dl in self.downloader_helper.get_configs().values():
                if f"{dl.name}_custom_tags" in config:
                    self._downloader_configs[dl.name] = {
                        "custom_tags": config.get(f"{dl.name}_custom_tags", "").split("\n")
                    }
        logger.info(f"{self.LOG_TAG} 初始化 完成")
    @eventmanager.register(EventType.DownloadAdded)
    def listen_download_added_event(self, event: Event = None):
        """
        监听下载添加事件
        """
        logger.info('监听到下载添加事件')
        if not self.get_state() :
            logger.warn('插件状态无效或未开启监听，忽略事件')
            return
        if not event or not event.event_data:
            logger.warn('事件信息无效，忽略事件')
            return
        # 执行
        logger.info('下载添加事件监听任务执行开始...')
        # enable_seeding=True是针对辅种添加种子并跳过校验的场景
        _hash = event.event_data.dict().get('hash')
        downloader = event.event_data.dict().get("downloader")
        service = self.downloader_helper.get_service(downloader)
        downloader_obj = service.instance
        if not service or not downloader_obj:
            logger.error(f"未获取到下载器：{downloader}")
            return
        if downloader_obj.is_inactive():
            logger.error(f"下载器 {downloader} 不在线")
            return
        
        # 获取下载器配置中的自定义标签
        tag = []
        logger.info(f"获取下载器 {downloader} 自定义标签")
        logger.info(f'配置为{self._downloader_configs}')
        if downloader in self._downloader_configs:
            tag.extend(self._downloader_configs[downloader].get("custom_tags", []))
        
        if service.type == "qbittorrent":
            downloader_obj.set_torrents_tag(ids=_hash, tags=tag)
        else:
            # 由于 tr 会覆盖原标签，此处设置追加
            _tags = downloader_obj.get_torrent_tags(ids=_hash)
            downloader_obj.set_torrent_tag(ids=_hash, tags=tag, org_tags=_tags)

        logger.info('下载添加事件监听任务执行结束')


    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        # 获取所有下载器配置
        downloader_configs = self.downloader_helper.get_configs()
        downloader_options = [{"title": dl.name, "value": dl.name} for dl in downloader_configs.values()]
        
        # 构建下载器配置表单
        downloader_forms = []
        for dl in downloader_configs.values():
            downloader_forms.append({
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12},
                        "content": [
                            {
                                "component": "VTextarea",
                                "props": {
                                    "model": f"{dl.name}_custom_tags",
                                    "label": f"{dl.name} - 自定义标签",
                                    "rows": 3,
                                    "placeholder": "每行一个标签\n例如：\n电影\n剧集\n动漫",
                                },
                            }
                        ]
                    }
                ]
            })

        return [
            {
                'component': 'VForm',
                'content': [
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
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': True,
                                            'chips': True,
                                            'clearable': True,
                                            'model': 'downloaders',
                                            'label': '下载器',
                                            'items': downloader_options
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    # 添加下载器独立配置表单
                    *downloader_forms,
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '每行配置一个，只会匹配一个，行数越高优先级越高。注意！！需用英文的:。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "cover": False,
            "site_first": False,
            # 初始化下载器自定义标签配置
            **{f"{dl.name}_custom_tags": "" for dl in downloader_configs.values()}
        }

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
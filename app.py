#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker管理Web界面
"""

import docker
from flask import Flask, render_template, request, jsonify
import logging
import os
import tempfile

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文JSON

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 简单认证配置（生产环境建议使用更复杂的认证机制）
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def check_auth():
    """简单认证检查"""
    from flask import re

def validate_container_name(name):
    """验证容器名称格式"""
    if not name:
        return False
    # 容器名称必须以字母或数字开头，只能包含字母、数字、下划线、点、连字符
    return bool(re.match(r'^[a-zA-Z0][a-zA-Z0_.-]*$', name))

def check_auth():
    """简单认证检查"""
    from flask import request
    auth = request.authorization
    if not auth or auth.username != ADMIN_USERNAME or auth.password != ADMIN_PASSWORD:
        return False
    return True

def require_auth(f):
    """认证装饰器"""
    from functools import wraps
    from flask import make_response
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_auth():
            return make_response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Docker Manager"'})
        return f(*args, **kwargs)
    return decorated_function

# 初始化Docker客户端
try:
    client = docker.from_env()
    logger.info("Docker客户端初始化成功")
except Exception as e:
    logger.error(f"Docker客户端初始化失败: {e}")
    client = None


@app.route('/')
@require_auth
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/containers')
@require_auth
def list_containers():
    """获取所有容器列表（不检查更新，快速返回）"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        containers = client.containers.list(all=True)
        container_list = []
        for container in containers:
            # 获取挂载点信息
            mounts = container.attrs.get('Mounts', [])
            volumes_info = []
            for mount in mounts:
                volume_info = {
                    'type': mount.get('Type', ''),
                    'source': mount.get('Source', ''),
                    'destination': mount.get('Destination', ''),
                    'mode': mount.get('Mode', 'rw')
                }
                volumes_info.append(volume_info)

            container_info = {
                'id': container.id[:12],
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                'status': '运行中' if container.status == 'running' else '已停止',
                'status_raw': container.status,
                'ports': container.ports,
                'volumes': volumes_info,
                'has_update': False,  # 不自动检查更新，通过检测更新按钮手动检查
            }
            container_list.append(container_info)
        return jsonify({'containers': container_list})
    except Exception as e:
        logger.error(f"获取容器列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/container/<container_id>/start', methods=['POST'])
@require_auth
def start_container(container_id):
    """启动容器"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        container = client.containers.get(container_id)
        container.start()
        return jsonify({'success': True, 'message': f'容器 {container_id} 已启动'})
    except Exception as e:
        logger.error(f"启动容器失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/container/<container_id>/stop', methods=['POST'])
@require_auth
def stop_container(container_id):
    """停止容器"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        container = client.containers.get(container_id)
        container.stop()
        return jsonify({'success': True, 'message': f'容器 {container_id} 已停止'})
    except Exception as e:
        logger.error(f"停止容器失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/container/<container_id>/restart', methods=['POST'])
@require_auth
def restart_container(container_id):
    """重启容器"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        container = client.containers.get(container_id)
        container.restart()
        return jsonify({'success': True, 'message': f'容器 {container_id} 已重启'})
    except Exception as e:
        logger.error(f"重启容器失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/container/<container_id>/logs')
@require_auth
def get_logs(container_id):
    """获取容器日志"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        # 获取行数参数，默认100行
        lines = request.args.get('lines', 100, type=int)

        container = client.containers.get(container_id)
        logs = container.logs(tail=lines).decode('utf-8')
        return jsonify({'logs': logs, 'container_id': container_id})
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return jsonify({'error': str(e)}), 500


def check_image_update(container):
    """检查容器镜像是否有更新（简化版，不拉取镜像）"""
    try:
        # 暂时不自动检测更新，只返回False
        # 避免网络问题导致卡住
        return False
    except Exception as e:
        logger.warning(f"检查更新失败: {e}")
        return False


@app.route('/api/container/<container_id>/pull', methods=['POST'])
@require_auth
def pull_image(container_id):
    """拉取镜像更新容器"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        container = client.containers.get(container_id)
        image_name = container.image.tags[0] if container.image.tags else container.image.id[:12]
        
        # 拉取最新镜像
        logger.info(f"开始拉取镜像: {image_name}")
        try:
            client.images.pull(image_name)
            message = f"镜像 {image_name} 拉取成功"
        except Exception as pull_err:
            # 如果拉取失败，尝试从镜像名提取
            logger.warning(f"拉取失败: {pull_err}")
            # 尝试使用默认镜像
            base_image = image_name.split(':')[0] if ':' in image_name else image_name
            try:
                client.images.pull(base_image)
                message = f"镜像 {base_image} 拉取成功"
            except Exception as e2:
                return jsonify({'error': f"拉取镜像失败: {str(e2)}"}), 500
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        logger.error(f"拉取镜像失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/container/<container_id>/update', methods=['POST'])
@require_auth
def update_container(container_id):
    """更新容器（重新创建）"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        container = client.containers.get(container_id)
        image_name = container.image.tags[0] if container.image.tags else container.image.id[:12]
        was_running = container.status == 'running'
        
        # 获取容器配置
        container_info = container.attrs
        env_vars = container_info.get('Config', {}).get('Env', [])
        cmd = container_info.get('Config', {}).get('Cmd')
        volumes = container_info.get('Mounts', [])
        ports = container_info.get('NetworkSettings', {}).get('Ports', {})
        
        # 拉取最新镜像
        try:
            client.images.pull(image_name)
        except:
            pass  # 继续尝试重新创建
        
        # 删除旧容器
        container.remove(force=was_running)
        
        # 重新创建容器
        new_container = client.containers.run(
            image_name,
            name=container_id,
            detach=True,
            environment=env_vars,
            command=cmd,
            volumes={v['Source']: {'bind': v['Destination'], 'mode': v['Mode']} for v in volumes if v.get('Source')},
            ports=ports,
            restart_policy={"Name": "unless-stopped"}
        )
        
        return jsonify({'success': True, 'message': f'容器 {container_id} 已更新'})
    except Exception as e:
        logger.error(f"更新容器失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-updates', methods=['POST'])
@require_auth
def check_updates():
    """检查所有容器镜像是否有更新"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        containers = client.containers.list(all=True)
        update_list = []
        container_status = {}  # 记录每个容器的更新状态

        for container in containers:
            try:
                logger.info(f"检查容器 {container.name} 的镜像更新...")
                has_update = check_image_update(container)
                container_status[container.id[:12]] = has_update

                if has_update:
                    image_name = container.image.tags[0] if container.image.tags else container.image.id[:12]
                    update_list.append({
                        'container_id': container.id[:12],
                        'container_name': container.name,
                        'image': image_name,
                        'has_update': True
                    })
            except Exception as e:
                logger.warning(f"检查容器 {container.name} 更新失败: {e}")

        logger.info(f"检测完成，发现 {len(update_list)} 个镜像有更新")
        return jsonify({
            'success': True,
            'total': len(containers),
            'updates': len(update_list),
            'update_list': update_list,
            'container_status': container_status,
            'message': f'检测完成，{len(update_list)}/{len(containers)} 个容器有更新'
        })
    except Exception as e:
        logger.error(f"检测更新失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/container/create', methods=['POST'])
@require_auth
def create_container():
    """创建新容器"""
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        data = request.json
        image_name = data.get('image', '').strip()
        container_name = data.get('name', '').strip()
        port_mappings = data.get('ports', '').strip()
        volume_mappings = data.get('volumes', '').strip()
        env_vars = data.get('env', '').strip()

        if not image_name:
            return jsonify({'error': '镜像名称不能为空'}), 400

        if not container_name:
            return jsonify({'error': '容器名称不能为空'}), 400

        # 验证容器名称格式
        if not validate_container_name(container_name):
            return jsonify({'error': '容器名称格式不正确，只能包含字母、数字、下划线、点、连字符，且以字母或数字开头'}), 400

        # 解析端口映射
        ports = {}
        if port_mappings:
            for mapping in port_mappings.split(','):
                mapping = mapping.strip()
                if ':' in mapping:
                    parts = mapping.split(':')
                    if len(parts) == 2:
                        host_port, container_port = parts
                        ports[f'{container_port}/tcp'] = int(host_port)
                        ports[f'{container_port}/udp'] = int(host_port)

        # 解析卷映射
        volumes = {}
        if volume_mappings:
            for mapping in volume_mappings.split(','):
                mapping = mapping.strip()
                if ':' in mapping:
                    parts = mapping.split(':')
                    if len(parts) >= 2:
                        host_path = parts[0]
                        container_path = parts[1]
                        mode = parts[2] if len(parts) > 2 else 'rw'
                        volumes[host_path] = {'bind': container_path, 'mode': mode}

        # 解析环境变量
        env_list = []
        if env_vars:
            for env in env_vars.split('\n'):
                env = env.strip()
                if env:
                    env_list.append(env)

        # 检查镜像是否存在，不存在则拉取
        try:
            client.images.get(image_name)
        except:
            logger.info(f"镜像 {image_name} 不存在，开始拉取...")
            try:
                client.images.pull(image_name)
                logger.info(f"镜像 {image_name} 拉取成功")
            except Exception as pull_err:
                return jsonify({'error': f'拉取镜像失败: {str(pull_err)}'}), 500

        # 创建容器
        container = client.containers.run(
            image_name,
            name=container_name,
            detach=True,
            ports=ports if ports else None,
            volumes=volumes if volumes else None,
            environment=env_list if env_list else None,
            restart_policy={"Name": "unless-stopped"}
        )

        logger.info(f"容器 {container_name} 创建成功")
        return jsonify({
            'success': True,
            'message': f'容器 {container_name} 创建成功',
            'container_id': container.id[:12]
        })
    except docker.errors.APIError as e:
        logger.error(f"创建容器失败: {e}")
        return jsonify({'error': f'创建失败: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"创建容器失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/compose/deploy', methods=['POST'])
@require_auth
def deploy_compose():
    """部署 Docker Compose 文件"""
    try:
        import yaml
    except ImportError:
        return jsonify({'error': 'YAML模块未安装，请先安装: pip install pyyaml'}), 500
    
    if not client:
        return jsonify({'error': 'Docker客户端未连接'}), 500

    try:
        data = request.json
        compose_content = data.get('compose_content', '').strip()

        if not compose_content:
            return jsonify({'error': 'Docker Compose 内容不能为空'}), 400

        # 解析 YAML
        try:
            compose_dict = yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            return jsonify({'error': f'YAML 解析失败: {str(e)}'}), 400

        if not compose_dict or 'services' not in compose_dict:
            return jsonify({'error': 'Docker Compose 文件缺少 services 定义'}), 400

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(compose_content)
            compose_file = f.name

        try:
            # 使用 docker SDK执行compose
            import subprocess
            import json
            
            # 使用docker compose命令（宿主机已安装）
            result = subprocess.run(
                ['docker', 'compose', '-f', compose_file, 'up', '-d', '--pull', 'missing'],
                capture_output=True,
                text=True,
                timeout=600,
                cwd='/tmp'
            )
            output = result.stdout
            error = result.stderr

            if result.returncode != 0:
                logger.error(f"docker compose 执行失败: {error}")
                return jsonify({'error': f'部署失败: {error}'}), 500

            logger.info(f"Docker Compose 部署成功: {output}")
            return jsonify({
                'success': True,
                'message': 'Docker Compose 部署成功',
                'output': output
            })

        finally:
            # 清理临时文件
            try:
                os.unlink(compose_file)
            except:
                pass

    except Exception as e:
        logger.error(f"部署 Docker Compose 失败: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # 生产环境关闭debug模式
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    # 从环境变量读取端口，默认8888
    port = int(os.environ.get('FLASK_PORT', 8888))
    app.run(host='0.0.0.0', port=port, debug=debug)

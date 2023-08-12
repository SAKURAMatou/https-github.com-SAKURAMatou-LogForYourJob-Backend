"""
用户设置相关接口
"""
import os
import uuid

from fastapi import APIRouter, Depends, Body, UploadFile, File

from dao.database import get_session
from dependencies import get_user_token
from usersetting.models import User
from usersetting.schema import UserCreate, UserBase, UserBasicInfoEdit
from utils.pathUtil import get_avatar_storage_path, makedir_if_missing
from utils.requestUtil import response
from utils.JWTUtil import hash_pwd
from logger.projectLogger import logger
from dao.commonModels import AttachmentFile, FileStorage
from PIL import Image

router = APIRouter(prefix='/usersetting')


@router.get('/detail')
async def get_user_details(user: UserBase = Depends(get_user_token)):
    return response.success('用户获取成功！', {'userinfo': user})


@logger.catch
@router.post('/change/userBaseInfo')
async def edit_user_basic_info(edit_user: UserBasicInfoEdit, user: User = Depends(get_user_token),
                               session=Depends(get_session)):
    try:
        """用户基本信息修改：名称，邮箱，头像"""
        if edit_user.name is not None:
            user.username = edit_user.name
        if edit_user.email is not None:
            user.useremail = edit_user.email
        if edit_user.avatarguid is not None:
            # 根据头像的guid找到对应的头像附件对象，并获取url
            pass
        session.commit()
        return return_user_info(user, '用户基本信息修改成功！')
    except Exception as e:
        session.rollback()
        return response.fail(535, '用户基本信息修改异常！')


@logger.catch
@router.post('/change/password')
async def edit_user_pwd(newpwd: str = Body(), user: User = Depends(get_user_token), session=Depends(get_session)):
    """用户密码修改"""
    try:
        user.pwd = hash_pwd(newpwd)
        session.commit()
        return return_user_info(user, '密码修改成功！')
    except Exception as e:
        session.rollback()
        return response.fail(535, '密码修改异常！')


@logger.catch
@router.post('/change/phone')
async def deit_user_phone(newphone: str = Body(), user: User = Depends(get_user_token), session=Depends(get_session)):
    """用户手机号修改"""
    try:
        user.phone = newphone
        session.commit()
        return return_user_info(user, '手机号修改成功！')
    except Exception as e:
        session.rollback()
        return response.fail(535, '手机号修改异常！')


async def return_user_info(user: User, msg: str):
    """用户信息返回函数"""
    return response.success(msg, {
        'userinfo': {'useremail': user.useremail, 'username': user.username, 'phone': user.phone,
                     'avatarurl': user.avatarurl}})


# 指定非必填 file: Union[UploadFile, None] = None或file: UploadFile = File(default=None)
@router.post('/change/avatar')
async def upload_avatar(file: UploadFile = File(description="upload avatar file"), user: User = Depends(get_user_token),
                        session=Depends(get_session)):
    """用户头像上传"""
    try:
        # 获取头像存储目录
        avatar_path = get_avatar_storage_path()
        # 检查头像存储的目录是否存在，不存在时新建
        makedir_if_missing(avatar_path)
        # 防止用户上传的文件名称过长之类的问题，保存的名称统一使用uuid生成保证长度统一
        storage_name = uuid.uuid4()
        file_type = file.filename.split(".")[-1]
        file_path = os.path.join(avatar_path, f'{storage_name}.{file_type}')

        with Image.open(file.file) as image:
            image = image.resize((100, 100))
            image.save(file_path)
        # 图片保存之后数据库记录图片信息
        attachment_file = AttachmentFile(rowguid=str(uuid.uuid4()), upload_userguid=user.rowguid)
        storage = FileStorage(rowguid=str(uuid.uuid4()), attachment_guid=attachment_file.rowguid)
        storage.storage_name = storage_name
        storage.type = file_type
        storage.file_size = file.size
        storage.file_name = file.filename
        storage.storage_path = file_path
        session.add(attachment_file)
        session.add(storage)
        session.commit()

        return response.success('头像上传成功！',
                                {'avatarguid': attachment_file.rowguid, 'url': file_path})


    except Exception as e:
        session.rollback()
        return response.fail(535, '头像上传异常！')

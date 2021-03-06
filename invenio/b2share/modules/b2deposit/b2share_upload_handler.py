# -*- coding: utf-8 -*-

## This file is part of B2SHARE.
## Copyright (C) 2013 EPCC, The University of Edinburgh.
##
## B2SHARE is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## B2SHARE is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with B2SHARE; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""
B2SHARE File Upload

Functions to handle plupload js calls from deposit page.
Based on WebDeposit code.
"""
import shutil
import os
from glob import iglob
import pickle

from werkzeug.utils import secure_filename

from flask import send_file, current_app


def encode_filename(filename):
    import hashlib
    hasher = hashlib.md5()
    hasher.update(filename.encode("utf-8"))
    md5 = hasher.hexdigest()
    safename = secure_filename(filename)
    return (safename, md5)

def get_extension(filename):
    root, ext = os.path.splitext(filename)
    if ext in ['.gz', '.bz2'] and root.endswith('.tar'):
        ext = ".tar" + ext
    return ext

def upload(request, sub_id):
    """ The file is split into chunks on the client-side
        and reformed on the server-side.

        @sub_id - submission id
    """
    if request.method == 'POST':
        if sub_id.startswith('/'):
            # malformed uuid, can lead to data escalation, raise an error
            raise Exception('UUID is malformed')

        try:
            chunks = request.form['chunks']
            chunk = request.form['chunk']
        except KeyError:
            chunks = None
            chunk = 0

        # the file name is guaranteed to be unique by the uploading js code
        name = request.form['name']
        current_chunk = request.files['file']


        CFG_B2SHARE_UPLOAD_FOLDER = current_app.config.get(
                                "CFG_B2SHARE_UPLOAD_FOLDER")

        if not os.path.exists(CFG_B2SHARE_UPLOAD_FOLDER):
            os.makedirs(CFG_B2SHARE_UPLOAD_FOLDER)

        # webdeposit also adds userid and deptype folders, we just use unique id
        upload_dir = os.path.join(CFG_B2SHARE_UPLOAD_FOLDER, sub_id)

        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        safename, md5 = encode_filename(name)

        # Save the chunk
        filename = safename + "_" + md5 + "_" + chunk
        path_to_save = os.path.join(upload_dir, filename)
        current_chunk.save(path_to_save)
        current_app.logger.info("uploaded chunk %s" % (filename,))

        if (chunks is None) or (int(chunk) == int(chunks) - 1):
            '''All chunks have been uploaded! Start merging the chunks!'''
            filename = merge_chunks_and_create_metadata(upload_dir, name, md5, safename)
        return filename

def merge_chunks_and_create_metadata(upload_dir, name, md5, safename):
    file_unique_name = safename + "_" + md5 + get_extension(safename)
    file_path = os.path.join(upload_dir, file_unique_name)

    chunk_files = []
    for chunk_file in iglob(os.path.join(upload_dir, safename + "_" + md5 + '_*')):
        chunk_files.append(chunk_file)
    # Sort files in numerical order
    chunk_files.sort(key=lambda x: int(x.split("_")[-1]))

    with open(file_path, 'wb') as destination:
        for chunk in chunk_files:
            with open(chunk, 'rb') as chunk_fd:
                shutil.copyfileobj(chunk_fd, destination)
            os.remove(chunk)
    return create_file_metadata(upload_dir, name, file_unique_name, file_path)

def create_file_metadata(upload_dir, name, file_unique_name, file_path):
    size = os.path.getsize(file_path)
    file_metadata = dict(name=name, file=file_path, size=size)

    # create a metadata_<uuid> file to store pickled metadata
    metadata_file_path = os.path.join(upload_dir, 'metadata_' + file_unique_name)
    pickle.dump(file_metadata, open(metadata_file_path, 'wb'))
    current_app.logger.info("finished uploading: %s, size %d, in %s" % (name, size, file_path))
    return file_unique_name

def delete(request, sub_id):
    """
    Deletes file and chunks of the file named form['filename'].

    Could change to return error if nothing deleted.
    """

    from flask import current_app

    result = ""

    CFG_B2SHARE_UPLOAD_FOLDER = current_app.config.get(
                            "CFG_B2SHARE_UPLOAD_FOLDER")

    upload_dir = os.path.join(CFG_B2SHARE_UPLOAD_FOLDER, sub_id)
    filename = request.form['filename']

    safename, md5 = encode_filename(filename)
    for chunk_file in iglob(os.path.join(upload_dir, safename + "_" + md5 + '_*')):
        os.remove(chunk_file)
        current_app.logger.info("deleted chunk: %s" % (chunk_file,))
        result = "Chunk " + chunk_file + " Deleted"

    file_unique_name = safename + "_" + md5 + get_extension(safename)
    metadata_file_path = os.path.join(upload_dir, 'metadata_' + file_unique_name)
    os.remove(metadata_file_path)
    current_app.logger.info("deleted metadata file: %s" % (metadata_file_path,))

    file_path = os.path.join(upload_dir, file_unique_name)
    os.remove(file_path)
    current_app.logger.info("deleted file: %s" % (file_path,))
    result = "File " + file_path + " Deleted"

    if result == "":
        current_app.logger.warning("cannot delete %s: not found" % (filename,))
        return "File " + filename + " not found", 404

    return result


def get_file(request, sub_id):
    """
    Returns uploaded file.

    I don't really think we need this, but it's easier to implement than to
    remove the functionality.
    """
    CFG_B2SHARE_UPLOAD_FOLDER = current_app.config.get(
                            "CFG_B2SHARE_UPLOAD_FOLDER")

    filename = request.args.get('filename')
    f = os.path.join(CFG_B2SHARE_UPLOAD_FOLDER, sub_id, filename)
    # make sure that request doesn't go outside the CFG_B2SHARE_UPLOAD_FOLDER
    if not os.path.samefile(
                            CFG_B2SHARE_UPLOAD_FOLDER,
                            os.path.commonprefix([CFG_B2SHARE_UPLOAD_FOLDER,
                              os.path.realpath(f)])):
        return "File " + filename + " not found", 404

    if (os.path.isfile(f)):
        return send_file(f, attachment_filename=filename, as_attachment=True)
    else:
        return "File " + filename + " not found", 404

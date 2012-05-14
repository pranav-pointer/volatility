# Volatility
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details. 
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA 

"""
@author:       Andrew Case
@license:      GNU General Public License 2.0 or later
@contact:      atcuno@gmail.com
@organization: Digital Forensics Solutions
"""

import volatility.commands as commands
import volatility.utils as utils
import volatility.debug as debug
import volatility.obj as obj

MAX_STRING_LENGTH = 256


def mask_number(num):
    return num & 0xffffffff


class AbstractLinuxCommand(commands.Command):

    def __init__(self, *args, **kwargs):
        commands.Command.__init__(self, *args, **kwargs)
        self.addr_space = utils.load_as(self._config)
        self.profile = self.addr_space.profile
        self.smap = self.profile.sysmap

    @staticmethod
    def is_valid_profile(profile):
        return profile.metadata.get('os', 'Unknown').lower() == 'linux'

# returns a list of online cpus (the processor numbers)
def online_cpus(smap, addr_space):

    #later kernels..
    if "cpu_online_bits" in smap:
        bmap = obj.Object("unsigned long", offset = smap["cpu_online_bits"], vm = addr_space)

    elif "cpu_present_map" in smap:
        bmap = obj.Object("unsigned long", offset = smap["cpu_present_map"], vm = addr_space)

    else:
        raise AttributeError, "Unable to determine number of online CPUs for memory capture"

    cpus = []
    for i in range(8):
        if bmap & (1 << i):
            cpus.append(i)

    return cpus

def walk_per_cpu_var(obj_ref, per_var, var_type):

    cpus = online_cpus(obj_ref.smap, obj_ref.addr_space)

    # get the highest numbered cpu
    max_cpu = cpus[-1]

    per_offsets = obj.Object(theType = 'Array', targetType = 'unsigned long', count = max_cpu, offset = obj_ref.smap["__per_cpu_offset"], vm = obj_ref.addr_space)
    i = 0

    for i in cpus:

        offset = per_offsets[i]

        addr = obj_ref.smap["per_cpu__" + per_var] + offset.v()
        var = obj.Object(var_type, offset = addr, vm = obj_ref.addr_space)

        yield i, var

# similar to for_each_process for this usage
def walk_list_head(struct_name, list_member, list_head_ptr, _addr_space):
    debug.warning("Deprecated use of walk_list_head")

    for item in list_head_ptr.list_of_type(struct_name, list_member):
        yield item


def walk_internal_list(struct_name, list_member, list_start, addr_space = None):
    if not addr_space:
        addr_space = list_start.obj_vm

    while list_start:
        list_struct = obj.Object(struct_name, vm = addr_space, offset = list_start.v())
        yield list_struct
        list_start = getattr(list_struct, list_member)


# based on __d_path
# TODO: (deleted) support
def do_get_path(rdentry, rmnt, dentry, vfsmnt):
    ret_path = []

    inode = dentry.d_inode

    while dentry != rdentry or vfsmnt != rmnt:

        dname = dentry.d_name.name.dereference_as("String", length = MAX_STRING_LENGTH)

        if dname != '/':
            ret_path.append(dname)

        if dentry == vfsmnt.mnt_root or dentry == dentry.d_parent:
            if vfsmnt.mnt_parent == vfsmnt:
                break
            dentry = vfsmnt.mnt_mountpoint
            vfsmnt = vfsmnt.mnt_parent
            continue

        parent = dentry.d_parent

        dentry = parent

    ret_path.reverse()

    ret_val = '/'.join([str(p) for p in ret_path])

    if ret_val.startswith(("socket:", "pipe:")):
        if ret_val.find("]") == -1:
            ret_val = ret_val[:-1] + "[{0}]".format(inode.i_ino)
        else:
            ret_val = ret_val.replace("/", "")

    elif ret_val != "inotify":
        ret_val = '/' + ret_val

    return ret_val


def get_path(task, filp):
    rdentry = task.fs.get_root_dentry()
    rmnt = task.fs.get_root_mnt()
    dentry = filp.get_dentry()
    vfsmnt = filp.get_vfsmnt()

    return do_get_path(rdentry, rmnt, dentry, vfsmnt)
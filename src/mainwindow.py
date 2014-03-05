from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic


TypeRole = Qt.UserRole + 1
OpaqueRefRole = Qt.UserRole + 2
PoolOpaqueRefRole = Qt.UserRole + 3
SortRole = Qt.UserRole + 4


class ItemDelegate(QItemDelegate):
    def sizeHint(self, option, index):
        return QSize(19, 19)


class TreeProxyFilter(QSortFilterProxyModel):
    def filterAcceptsRow(self, sourceRow, sourceParent):
        index = self.sourceModel().index(sourceRow, 0, sourceParent)
        return self._showThis(index)

    def _showThis(self, index):
        if self.sourceModel().rowCount(index) > 0:
            for i in range(self.sourceModel().rowCount(index)):
                # return also parent nodes even when child not match
                if self.sourceModel().data(index, Qt.DisplayRole).toString().contains(self.filterRegExp()):
                    return True

                child_index = self.sourceModel().index(i, 0, index)
                if not child_index.isValid():
                    break
                ret = self._showThis(child_index)
                if ret:
                    return ret
        else:
            use_index = self.sourceModel().index(index.row(), 0, index.parent())
            _type = self.sourceModel().data(use_index, Qt.DisplayRole).toString()
            if not _type.contains(self.filterRegExp()):
                return False
            else:
                return True

        return False

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        uic.loadUi("ui/MainWindow.ui", self)

        # xapi connection manager
        self.xcm = None

        self.treeViewModel = QStandardItemModel(0, 1, self)

        self.treeViewProxyModel = TreeProxyFilter()
        self.treeViewProxyModel.setSourceModel(self.treeViewModel)
        self.treeViewProxyModel.setSortRole(SortRole)

        delegate = ItemDelegate()

        self.treeView.setModel(self.treeViewProxyModel)
        self.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.treeView.setItemDelegate(delegate)
        self.treeView.setSortingEnabled(True)
        self.treeView.setHeaderHidden(True)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)

        QObject.connect(self.treeView, SIGNAL("customContextMenuRequested(QPoint)"), self.onTreeViewCustomContextMenuRequest)
        QObject.connect(self.treeView, SIGNAL("clicked(QModelIndex)"), self.onTreeViewItemClick)

        QObject.connect(self.treeFilter, SIGNAL("textChanged(QString)"), self.onTreeFilterChanged)

    def _getPoolModel(self, pool_ref):
        pool_row = None
        for i in range(self.treeViewModel.rowCount()):
            if self.treeViewModel.item(i, 0).data(role=TypeRole).toString() != 'pool':
                continue
            if self.treeViewModel.item(i, 0).data(role=OpaqueRefRole).toString() == pool_ref:
                pool_row = i
                break

        if pool_row == None:
            return None

        return self.treeViewModel.item(pool_row, 0)

    def _getHostModel(self, pool_ref, host_ref):
        pool_model = self._getPoolModel(pool_ref)
        host_row = None
        for i in range(pool_model.rowCount()):
            if pool_model.child(i, 0).data(role=TypeRole).toString() != 'host':
                continue
            if pool_model.child(i, 0).data(role=OpaqueRefRole).toString() == host_ref:
                return pool_model.child(i, 0)

        return None

    def _getVmModel(self, pool_ref, vm_ref, vm_data):
        # search for global vms
        host = self._getVmHost(vm_data)
        if host:
            model = self._getHostModel(pool_ref, host)
        else:
            model = self._getPoolModel(pool_ref)

        for i in range(model.rowCount()):
            if model.child(i, 0).data(role=TypeRole).toString() != 'vm':
                continue
            if model.child(i, 0).data(role=OpaqueRefRole).toString() == vm_ref:
                return model.child(i, 0)

        return None

    def _setVmObject(self, vm_obj, vm_ref, vm_data):
        vm_obj.setText(vm_data['name_label'])
        vm_obj.setData('vm', role=TypeRole)
        vm_obj.setData(vm_ref, role=OpaqueRefRole)
        vm_obj.setData('1:vm/{0}'.format(vm_data['name_label']), role=SortRole)

        if vm_data['current_operations'] != {}:
            vm_obj.setIcon(QIcon('icons/lightning.png'))
        elif vm_data['power_state'] == 'Halted':
            vm_obj.setIcon(QIcon('icons/status-busy.png'))
        elif vm_data['power_state'] == 'Paused':
            vm_obj.setIcon(QIcon('icons/status-away.png'))
        elif vm_data['power_state'] == 'Running':
            vm_obj.setIcon(QIcon('icons/status.png'))
        elif vm_data['power_state'] == 'Suspended':
            vm_obj.setIcon(QIcon('icons/status-away.png'))
        else:
            raise Exception("Unknown power state: {0}".format(vm_data['power_state']))

    def _getVmHost(self, vm_data):
        if vm_data['affinity'] == 'OpaqueRef:NULL' and vm_data['resident_on'] == 'OpaqueRef:NULL':
            # should be assigned to pool
            return None
        elif vm_data['resident_on'] != 'OpaqueRef:NULL':
            # FIXME: need to check if it has local storage and return host that contains disk
            return vm_data['resident_on']
        elif vm_data['affinity'] != 'OpaqueRef:NULL':
            return vm_data['affinity']
        else:
            raise Exception("Unexpected host assignment!")

    def _addVmToTree(self, pool_ref, vm_ref, vm_data):
        if vm_data['is_control_domain'] or vm_data['is_a_template']:
            return

        vm = QStandardItem()
        self._setVmObject(vm, vm_ref, vm_data)
        vm.setData(pool_ref, role=PoolOpaqueRefRole)

        host = self._getVmHost(vm_data)
        if host:
            self._getHostModel(pool_ref, host).appendRow(vm)
        else:
            self._getPoolModel(pool_ref).appendRow(vm)

    def _setSrObject(self, sr_obj, sr_ref, sr_data):
        sr_obj.setText(sr_data['name_label'])
        sr_obj.setData('sr', role=TypeRole)
        sr_obj.setData(sr_ref, role=OpaqueRefRole)
        sr_obj.setData('2:sr/{0}'.format(sr_data['name_label']), role=SortRole)

        sr_obj.setIcon(QIcon('icons/database.png'))

    def _addSrToTree(self, pool_ref, sr_ref, sr_data):
        sr = QStandardItem()
        self._setSrObject(sr, sr_ref, sr_data)

        if sr_data['shared'] == True:
            self._getPoolModel(pool_ref).appendRow(sr)
        else:
            self._getHostModel(pool_ref,
                self.xcm.getConnectionByPoolRef(pool_ref).data['pbd'][sr_data['PBDs'][0]]['host']).appendRow(sr)

    def onTreeFilterChanged(self, text):
        self.treeViewProxyModel.setFilterRegExp(QRegExp(text,
            Qt.CaseInsensitive, QRegExp.FixedString));
        self.treeViewProxyModel.setFilterKeyColumn(0);
        if text:
            self.treeView.expandAll()
        else:
            for i in range(self.treeViewModel.rowCount()):
                pool_model = self.treeViewModel.item(i, 0)
                self.treeView.setExpanded(self.treeViewModel.item(i, 0).index(), True)
                for j in range(pool_model.rowCount()):
                    # FIXME doesn't de-expand, don't know why yet
                    self.treeView.setExpanded(pool_model.child(j, 0).index(), False)

    def onTreeViewItemClick(self, index):
        m = self.treeViewModel.itemFromIndex(self.treeViewProxyModel.mapToSource(index))

    def onTreeViewCustomContextMenuRequest(self, pos):
        index = self.treeView.selectedIndexes()[0]
        m = self.treeViewModel.itemFromIndex(self.treeViewProxyModel.mapToSource(index))

        menu = QMenu()
        menu.addAction(self.actionStart)
        menu.addAction(self.actionSuspend)
        menu.addAction(self.actionShutdown)
        menu.addSeparator()
        #menu.addAction(actionProperties)
        menu.exec_(self.treeView.mapToGlobal(pos))

    def onConnectionSuccessful(self, pool_ref, conn):
        pool_name = conn.data['pool'][pool_ref]['name_label']
        pool = QStandardItem(QIcon('icons/servers.png'),
                             pool_name)
        pool.setData('pool', role=TypeRole)
        pool.setData(pool_ref, role=OpaqueRefRole)
        pool.setData(pool_name, role=SortRole)

        self.treeViewModel.appendRow(pool)

        for host_ref, host_data in conn.data['host'].items():
            host = QStandardItem(QIcon('icons/server.png'),
                                 host_data['name_label'])
            host.setData('host', role=TypeRole)
            host.setData(host_ref, role=OpaqueRefRole)
            host.setData('0:host/{0}'.format(host_data['name_label']), role=SortRole)

            pool.appendRow(host)
            self.treeView.setExpanded(host.index(), False)

        for vm_ref, vm_data in conn.data['vm'].items():
            self._addVmToTree(pool_ref, vm_ref, vm_data)

        for sr_ref, sr_data in conn.data['sr'].items():
            self._addSrToTree(pool_ref, sr_ref, sr_data)

        self.treeView.sortByColumn(0, Qt.AscendingOrder)
        self.treeView.setExpanded(pool.index(), True)

    def onConnectionFailed(self, pool_ref, data):
        pass

    def _findHostInTree(self, pool_ref, vm_data):
        """Returns host model"""
        pool_row = None
        for i in range(self.treeViewModel.rowCount()):
            if self.treeViewModel.item(i, 0).data(role=OpaqueRefRole).toString() == pool_ref:
                pool_row = i
                break

        if pool_row == None:
            return

        host_row = None
        pool_model = self.treeViewModel.item(pool_row, 0)

        for i in range(pool_model.rowCount()):
            if pool_model.child(i, 0).data(role=TypeRole).toString() != 'host':
                continue
            if pool_model.child(i, 0).data(role=OpaqueRefRole).toString() == vm_data['affinity'] or pool_model.child(i, 0).data(role=OpaqueRefRole).toString() == vm_data['resident_on']:
                host_row = i
                break

        if host_row == None:
            return None

        return pool_model.child(host_row, 0)

    def _findVmInTree(self, pool_ref, vm_ref, vm_data):
        """Returns vm model"""
        host_model = self._findHostInTree(pool_ref, vm_data)

        if host_model == None:
            return None

        vm_row = None
        for i in range(host_model.rowCount()):
            if host_model.child(i, 0).data(role=TypeRole).toString() != 'vm':
                continue
            if host_model.child(i, 0).data(role=OpaqueRefRole).toString() == vm_ref:
                vm_row = i
                break

        if vm_row == None:
            return None

        return host_model.child(vm_row, 0)

    # this actually removes old node and creates new one
    def _moveVmInTree(self, pool_ref, vm_ref, vm_data):
        current_selection = self.treeView.selectedIndexes()

        # create new item
        self._addVmToTree(pool_ref, vm_ref, vm_data)

        # if node was previously selected, select new node
        if self._findVmInTree(pool_ref, vm_ref, vm_data).data(role=OpaqueRefRole).toString() == vm_ref:
            self.treeView.setCurrentIndex(self._findVmInTree(pool_ref, vm_ref, vm_data).index())

        # remove old item
        pool_row = None
        for i in range(self.treeViewModel.rowCount()):
            if self.treeViewModel.item(i, 0).data(role=OpaqueRefRole).toString() == pool_ref:
                pool_row = i
                break

        if pool_row == None:
            return

        host_row = None
        pool_model = self.treeViewModel.item(pool_row, 0)

        _is_removed = False
        for i in range(pool_model.rowCount()):
            if _is_removed:
                break

            if pool_model.child(i, 0).data(role=TypeRole).toString() == 'vm':
                self.treeViewModel.removeRow(i)
                break
            if pool_model.child(i, 0).data(role=TypeRole).toString() == 'host':
                if pool_model.child(i, 0).data(role=OpaqueRefRole).toString() == vm_data['resident_on']:
                    continue

                host_model = pool_model.child(i, 0)
                for j in range(host_model.rowCount()):
                    if host_model.child(j, 0).data(role=TypeRole).toString() != 'vm':
                        continue
                    if host_model.child(j, 0).data(role=OpaqueRefRole).toString() == vm_ref:
                        host_model.removeRow(j)
                        _is_removed = True
                        break

    def onVmAdded(self, pool_ref, vm_ref, vm_data):
        self._addVmToTree(pool_ref, vm_ref, vm_data)
        self.treeView.sortByColumn(0, Qt.AscendingOrder)

    def onVmModified(self, pool_ref, vm_ref, vm_data):
        vm = self._getVmModel(pool_ref, vm_ref, vm_data)
        # somethimes we don't have correct vm
        # for example: when we starting vm from template, then we can get vm_ref
        # which is vm template actually
        if not vm:
            self._moveVmInTree(pool_ref, vm_ref, vm_data)
            return
        self._setVmObject(vm, vm_ref, vm_data)
        self.treeView.sortByColumn(0, Qt.AscendingOrder)

    def onVmDeleted(self, pool_ref, vm_ref, vm_data):
        vm = self._getVmModel(pool_ref, vm_ref, vm_data)
        vm.parent().removeRow(vm.index().row())
        self.treeView.sortByColumn(0, Qt.AscendingOrder)

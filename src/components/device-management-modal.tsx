'use client'

import React, { useState, useEffect } from 'react'
import { X, Trash2, Edit2, ToggleLeft, ToggleRight, Save, AlertCircle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

interface DeviceInfo {
  device_ip: string
  alias: string
  model: string
  device_type: string
  mac: string
  last_seen: string
  is_monitored: boolean
  discovered_at: string
  user_notes: string | null
}

interface DeviceManagementModalProps {
  isOpen: boolean
  onClose: () => void
}

export function DeviceManagementModal({ isOpen, onClose }: DeviceManagementModalProps) {
  const queryClient = useQueryClient()
  const [editingDevice, setEditingDevice] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<{ [key: string]: { ip: string; notes: string } }>({})
  const [error, setError] = useState<string | null>(null)

  const { data: devices = [], refetch } = useQuery({
    queryKey: ['saved-devices'],
    queryFn: async () => {
      const res = await fetch('/api/devices/saved')
      return res.json()
    },
    enabled: isOpen
  })

  const updateMonitoringMutation = useMutation({
    mutationFn: async ({ deviceIp, enabled }: { deviceIp: string; enabled: boolean }) => {
      const res = await fetch(`/api/devices/${deviceIp}/monitoring`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      })
      if (!res.ok) throw new Error('Failed to update monitoring')
      return res.json()
    },
    onSuccess: () => {
      refetch()
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    }
  })

  const updateIpMutation = useMutation({
    mutationFn: async ({ oldIp, newIp }: { oldIp: string; newIp: string }) => {
      const res = await fetch(`/api/devices/${oldIp}/ip`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_ip: newIp })
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to update IP')
      }
      return res.json()
    },
    onSuccess: () => {
      setEditingDevice(null)
      setEditValues({})
      refetch()
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    },
    onError: (error: any) => {
      setError(error.message)
    }
  })

  const updateNotesMutation = useMutation({
    mutationFn: async ({ deviceIp, notes }: { deviceIp: string; notes: string }) => {
      const res = await fetch(`/api/devices/${deviceIp}/notes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes })
      })
      if (!res.ok) throw new Error('Failed to update notes')
      return res.json()
    },
    onSuccess: () => {
      setEditingDevice(null)
      setEditValues({})
      refetch()
    }
  })

  const removeDeviceMutation = useMutation({
    mutationFn: async (deviceIp: string) => {
      const res = await fetch(`/api/devices/${deviceIp}`, {
        method: 'DELETE'
      })
      if (!res.ok) throw new Error('Failed to remove device')
      return res.json()
    },
    onSuccess: () => {
      refetch()
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    }
  })

  const handleEdit = (device: DeviceInfo) => {
    setEditingDevice(device.device_ip)
    setEditValues({
      ...editValues,
      [device.device_ip]: {
        ip: device.device_ip,
        notes: device.user_notes || ''
      }
    })
    setError(null)
  }

  const handleSave = (device: DeviceInfo) => {
    const values = editValues[device.device_ip]
    if (!values) return

    // Update IP if changed
    if (values.ip !== device.device_ip) {
      updateIpMutation.mutate({ oldIp: device.device_ip, newIp: values.ip })
    }

    // Update notes if changed
    if (values.notes !== (device.user_notes || '')) {
      updateNotesMutation.mutate({ deviceIp: device.device_ip, notes: values.notes })
    }

    if (values.ip === device.device_ip && values.notes === (device.user_notes || '')) {
      setEditingDevice(null)
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'Never'
    return new Date(dateStr).toLocaleString()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">Device Management</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <span className="text-red-800">{error}</span>
            </div>
          )}

          {devices.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No devices have been discovered yet.</p>
          ) : (
            <div className="space-y-4">
              {devices.map((device: DeviceInfo) => (
                <div
                  key={device.device_ip}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-4 mb-2">
                        <h3 className="text-lg font-semibold">{device.alias}</h3>
                        <span className="text-sm text-gray-500">{device.model}</span>
                        <button
                          onClick={() => updateMonitoringMutation.mutate({
                            deviceIp: device.device_ip,
                            enabled: !device.is_monitored
                          })}
                          className={`flex items-center gap-2 px-3 py-1 rounded-lg transition-colors ${
                            device.is_monitored
                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {device.is_monitored ? (
                            <>
                              <ToggleRight className="h-4 w-4" />
                              <span>Monitoring</span>
                            </>
                          ) : (
                            <>
                              <ToggleLeft className="h-4 w-4" />
                              <span>Not Monitoring</span>
                            </>
                          )}
                        </button>
                      </div>

                      {editingDevice === device.device_ip ? (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              IP Address
                            </label>
                            <input
                              type="text"
                              value={editValues[device.device_ip]?.ip || ''}
                              onChange={(e) => setEditValues({
                                ...editValues,
                                [device.device_ip]: {
                                  ...editValues[device.device_ip],
                                  ip: e.target.value
                                }
                              })}
                              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="192.168.1.100"
                            />
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Notes
                            </label>
                            <textarea
                              value={editValues[device.device_ip]?.notes || ''}
                              onChange={(e) => setEditValues({
                                ...editValues,
                                [device.device_ip]: {
                                  ...editValues[device.device_ip],
                                  notes: e.target.value
                                }
                              })}
                              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                              rows={2}
                              placeholder="Add notes about this device..."
                            />
                          </div>

                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSave(device)}
                              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                            >
                              <Save className="h-4 w-4" />
                              Save
                            </button>
                            <button
                              onClick={() => {
                                setEditingDevice(null)
                                setEditValues({})
                                setError(null)
                              }}
                              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">IP:</span> {device.device_ip}
                          </p>
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">MAC:</span> {device.mac}
                          </p>
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Type:</span> {device.device_type}
                          </p>
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Last Seen:</span> {formatDate(device.last_seen)}
                          </p>
                          {device.user_notes && (
                            <p className="text-sm text-gray-600 mt-2">
                              <span className="font-medium">Notes:</span> {device.user_notes}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {editingDevice !== device.device_ip && (
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleEdit(device)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit device"
                        >
                          <Edit2 className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Are you sure you want to remove ${device.alias}? All historical data will be deleted.`)) {
                              removeDeviceMutation.mutate(device.device_ip)
                            }
                          }}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Remove device"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
'use client'

import { useState, useEffect } from 'react'
import { X, DollarSign, Clock, Save, Plus, Trash2, Info } from 'lucide-react'
import axios from 'axios'

interface ElectricityRatesModalProps {
  onClose: () => void
}

type RateType = 'flat' | 'time_of_use' | 'tiered' | 'seasonal' | 'combined' | 'seasonal_tiered'

interface TimeOfUseRate {
  start_hour: number
  end_hour: number
  rate_per_kwh: number
  days_of_week?: number[]
  description?: string
}

interface TierRate {
  min_kwh: number
  max_kwh?: number
  rate_per_kwh: number
  description?: string
}

interface SeasonalRate {
  start_month: number
  end_month: number
  base_rate: number
  tier_rates?: TierRate[]
  description?: string
}

export function ElectricityRatesModal({ onClose }: ElectricityRatesModalProps) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  
  const [formData, setFormData] = useState({
    name: 'My Electricity Rate',
    rate_type: 'flat' as RateType,
    currency: 'USD',
    
    // Flat rate
    flat_rate: 0.12,
    
    // Time-of-use rates
    time_of_use_rates: [] as TimeOfUseRate[],
    
    // Tiered rates
    tier_rates: [] as TierRate[],
    
    // Seasonal rates
    seasonal_rates: [] as SeasonalRate[],
    
    // Additional charges
    monthly_service_charge: 0,
    demand_charge_per_kw: 0,
    tax_rate: 0,
    
    // Metadata
    utility_provider: '',
    rate_schedule: '',
    notes: ''
  })

  useEffect(() => {
    loadRates()
  }, [])

  const loadRates = async () => {
    try {
      setLoading(true)
      const response = await axios.get('/api/rates')
      if (response.data.length > 0) {
        const rate = response.data[0]
        setFormData({
          ...formData,
          ...rate,
          time_of_use_rates: rate.time_of_use_rates || [],
          tier_rates: rate.tier_rates || [],
          seasonal_rates: rate.seasonal_rates || []
        })
      }
    } catch (error) {
      console.error('Failed to load rates:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await axios.post('/api/rates', formData)
      setTimeout(onClose, 1000)
    } catch (error) {
      console.error('Failed to save rates:', error)
      alert('Failed to save rates. Please check your configuration.')
    } finally {
      setSaving(false)
    }
  }

  const addTimeOfUseRate = () => {
    setFormData({
      ...formData,
      time_of_use_rates: [
        ...formData.time_of_use_rates,
        {
          start_hour: 14,
          end_hour: 20,
          rate_per_kwh: 0.25,
          description: 'Peak Hours'
        }
      ]
    })
  }

  const removeTimeOfUseRate = (index: number) => {
    setFormData({
      ...formData,
      time_of_use_rates: formData.time_of_use_rates.filter((_, i) => i !== index)
    })
  }

  const updateTimeOfUseRate = (index: number, field: string, value: any) => {
    const updated = [...formData.time_of_use_rates]
    updated[index] = { ...updated[index], [field]: value }
    setFormData({ ...formData, time_of_use_rates: updated })
  }

  const addTierRate = () => {
    const lastTier = formData.tier_rates[formData.tier_rates.length - 1]
    const newMinKwh = lastTier ? (lastTier.max_kwh || 1000) : 0
    
    setFormData({
      ...formData,
      tier_rates: [
        ...formData.tier_rates,
        {
          min_kwh: newMinKwh,
          max_kwh: formData.tier_rates.length === 0 ? 100 : undefined,
          rate_per_kwh: 0.10 + (formData.tier_rates.length * 0.02),
          description: `Tier ${formData.tier_rates.length + 1}`
        }
      ]
    })
  }

  const removeTierRate = (index: number) => {
    setFormData({
      ...formData,
      tier_rates: formData.tier_rates.filter((_, i) => i !== index)
    })
  }

  const updateTierRate = (index: number, field: string, value: any) => {
    const updated = [...formData.tier_rates]
    updated[index] = { ...updated[index], [field]: value }
    
    // Auto-adjust next tier's min_kwh when max_kwh changes
    if (field === 'max_kwh' && value && index < updated.length - 1) {
      updated[index + 1].min_kwh = parseFloat(value)
    }
    
    setFormData({ ...formData, tier_rates: updated })
  }

  const addSeasonalRate = () => {
    setFormData({
      ...formData,
      seasonal_rates: [
        ...formData.seasonal_rates,
        {
          start_month: 6,
          end_month: 9,
          base_rate: 0.15,
          description: 'Summer'
        }
      ]
    })
  }

  const removeSeasonalRate = (index: number) => {
    setFormData({
      ...formData,
      seasonal_rates: formData.seasonal_rates.filter((_, i) => i !== index)
    })
  }

  const updateSeasonalRate = (index: number, field: string, value: any) => {
    const updated = [...formData.seasonal_rates]
    updated[index] = { ...updated[index], [field]: value }
    setFormData({ ...formData, seasonal_rates: updated })
  }

  const addSeasonTier = (seasonIndex: number) => {
    const updated = [...formData.seasonal_rates]
    if (!updated[seasonIndex].tier_rates) {
      updated[seasonIndex].tier_rates = []
    }
    
    const lastTier = updated[seasonIndex].tier_rates![updated[seasonIndex].tier_rates!.length - 1]
    const newMinKwh = lastTier ? (lastTier.max_kwh || 1000) : 0
    
    updated[seasonIndex].tier_rates!.push({
      min_kwh: newMinKwh,
      max_kwh: updated[seasonIndex].tier_rates!.length === 0 ? 100 : undefined,
      rate_per_kwh: 0.10 + (updated[seasonIndex].tier_rates!.length * 0.02),
      description: `Tier ${updated[seasonIndex].tier_rates!.length + 1}`
    })
    setFormData({ ...formData, seasonal_rates: updated })
  }

  const removeSeasonTier = (seasonIndex: number, tierIndex: number) => {
    const updated = [...formData.seasonal_rates]
    updated[seasonIndex].tier_rates = updated[seasonIndex].tier_rates?.filter((_, i) => i !== tierIndex)
    setFormData({ ...formData, seasonal_rates: updated })
  }

  const updateSeasonTier = (seasonIndex: number, tierIndex: number, field: string, value: any) => {
    const updated = [...formData.seasonal_rates]
    if (updated[seasonIndex].tier_rates) {
      updated[seasonIndex].tier_rates[tierIndex] = { 
        ...updated[seasonIndex].tier_rates[tierIndex], 
        [field]: value 
      }
    }
    setFormData({ ...formData, seasonal_rates: updated })
  }

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 z-10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Electricity Rate Configuration</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Basic Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rate Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Currency
                </label>
                <select
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="CAD">CAD ($)</option>
                  <option value="AUD">AUD ($)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Utility Provider
                </label>
                <input
                  type="text"
                  value={formData.utility_provider}
                  onChange={(e) => setFormData({ ...formData, utility_provider: e.target.value })}
                  placeholder="e.g., Pacific Gas & Electric"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rate Schedule
                </label>
                <input
                  type="text"
                  value={formData.rate_schedule}
                  onChange={(e) => setFormData({ ...formData, rate_schedule: e.target.value })}
                  placeholder="e.g., E-TOU-C"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
              </div>
            </div>
          </div>

          {/* Rate Type Selection */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Rate Structure</h3>
            
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Select Rate Type
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {[
                  { value: 'flat', label: 'Flat Rate', desc: 'Single rate for all usage' },
                  { value: 'time_of_use', label: 'Time-of-Use', desc: 'Different rates by time' },
                  { value: 'tiered', label: 'Tiered', desc: 'Rates based on usage levels' },
                  { value: 'seasonal', label: 'Seasonal', desc: 'Rates vary by season' },
                  { value: 'combined', label: 'TOU + Tiered', desc: 'Time-of-use with tiers' },
                  { value: 'seasonal_tiered', label: 'Seasonal + Tiered', desc: 'Seasonal with tiers' }
                ].map((type) => (
                  <button
                    key={type.value}
                    onClick={() => setFormData({ ...formData, rate_type: type.value as RateType })}
                    className={`p-3 border rounded-lg text-left transition-colors ${
                      formData.rate_type === type.value
                        ? 'border-kasa-primary bg-green-50'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="font-medium">{type.label}</div>
                    <div className="text-xs text-gray-500">{type.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Rate Configuration Based on Type */}
          {formData.rate_type === 'flat' && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-semibold mb-3">Flat Rate Configuration</h4>
              <div className="flex items-center space-x-2">
                <DollarSign className="h-5 w-5 text-gray-400" />
                <input
                  type="number"
                  step="0.001"
                  value={formData.flat_rate}
                  onChange={(e) => setFormData({ ...formData, flat_rate: parseFloat(e.target.value) })}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
                <span className="text-gray-600">per kWh</span>
              </div>
            </div>
          )}

          {(formData.rate_type === 'time_of_use' || formData.rate_type === 'combined') && (
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold">Time-of-Use Rates</h4>
                <button
                  onClick={addTimeOfUseRate}
                  className="flex items-center space-x-1 px-3 py-1 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Period</span>
                </button>
              </div>
              
              {formData.time_of_use_rates.length === 0 ? (
                <p className="text-gray-500 text-sm">No time-of-use periods configured. Click "Add Period" to start.</p>
              ) : (
                <div className="space-y-3">
                  {formData.time_of_use_rates.map((rate, index) => (
                    <div key={index} className="bg-white rounded-lg p-3 border border-blue-200">
                      <div className="flex items-start justify-between mb-2">
                        <input
                          type="text"
                          value={rate.description || ''}
                          onChange={(e) => updateTimeOfUseRate(index, 'description', e.target.value)}
                          placeholder="Period name (e.g., Peak Hours)"
                          className="text-sm font-medium bg-transparent border-b border-gray-300 focus:outline-none focus:border-blue-500"
                        />
                        <button
                          onClick={() => removeTimeOfUseRate(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="text-xs text-gray-600">Start Hour</label>
                          <select
                            value={rate.start_hour}
                            onChange={(e) => updateTimeOfUseRate(index, 'start_hour', parseInt(e.target.value))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            {Array.from({ length: 24 }, (_, i) => (
                              <option key={i} value={i}>
                                {i.toString().padStart(2, '0')}:00
                              </option>
                            ))}
                          </select>
                        </div>
                        
                        <div>
                          <label className="text-xs text-gray-600">End Hour</label>
                          <select
                            value={rate.end_hour}
                            onChange={(e) => updateTimeOfUseRate(index, 'end_hour', parseInt(e.target.value))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            {Array.from({ length: 24 }, (_, i) => (
                              <option key={i} value={i}>
                                {i.toString().padStart(2, '0')}:00
                              </option>
                            ))}
                          </select>
                        </div>
                        
                        <div>
                          <label className="text-xs text-gray-600">Rate ($/kWh)</label>
                          <input
                            type="number"
                            step="0.001"
                            value={rate.rate_per_kwh}
                            onChange={(e) => updateTimeOfUseRate(index, 'rate_per_kwh', parseFloat(e.target.value))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {(formData.rate_type === 'tiered' || formData.rate_type === 'combined') && (
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold">Tiered Rates</h4>
                <button
                  onClick={addTierRate}
                  className="flex items-center space-x-1 px-3 py-1 bg-green-500 text-white rounded-lg hover:bg-green-600"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Tier</span>
                </button>
              </div>
              
              {formData.tier_rates.length === 0 ? (
                <p className="text-gray-500 text-sm">No tiers configured. Click "Add Tier" to start.</p>
              ) : (
                <div className="space-y-3">
                  {formData.tier_rates.map((tier, index) => (
                    <div key={index} className="bg-white rounded-lg p-3 border border-green-200">
                      <div className="flex items-center justify-between mb-2">
                        <input
                          type="text"
                          value={tier.description || `Tier ${index + 1}`}
                          onChange={(e) => updateTierRate(index, 'description', e.target.value)}
                          placeholder="Tier name"
                          className="text-sm font-medium bg-transparent border-b border-gray-300 focus:outline-none focus:border-green-500"
                        />
                        <button
                          onClick={() => removeTierRate(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="text-xs text-gray-600">Min kWh</label>
                          <input
                            type="number"
                            step="1"
                            value={tier.min_kwh}
                            onChange={(e) => updateTierRate(index, 'min_kwh', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                            disabled={index > 0}  // Auto-set from previous tier
                          />
                        </div>
                        
                        <div>
                          <label className="text-xs text-gray-600">Max kWh</label>
                          <input
                            type="number"
                            step="1"
                            value={tier.max_kwh || ''}
                            onChange={(e) => updateTierRate(index, 'max_kwh', e.target.value ? parseFloat(e.target.value) : undefined)}
                            placeholder="Unlimited"
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                          />
                        </div>
                        
                        <div>
                          <label className="text-xs text-gray-600">Rate ($/kWh)</label>
                          <input
                            type="number"
                            step="0.001"
                            value={tier.rate_per_kwh}
                            onChange={(e) => updateTierRate(index, 'rate_per_kwh', parseFloat(e.target.value))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                          />
                        </div>
                      </div>
                      
                      <div className="text-xs text-gray-500 mt-1">
                        Usage Range: {tier.min_kwh} - {tier.max_kwh || 'Unlimited'} kWh
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {(formData.rate_type === 'seasonal' || formData.rate_type === 'seasonal_tiered') && (
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold">Seasonal Rates</h4>
                <button
                  onClick={addSeasonalRate}
                  className="flex items-center space-x-1 px-3 py-1 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Season</span>
                </button>
              </div>
              
              {formData.seasonal_rates.length === 0 ? (
                <p className="text-gray-500 text-sm">No seasons configured. Click "Add Season" to start.</p>
              ) : (
                <div className="space-y-3">
                  {formData.seasonal_rates.map((season, index) => (
                    <div key={index} className="bg-white rounded-lg p-3 border border-yellow-200">
                      <div className="flex items-center justify-between mb-2">
                        <input
                          type="text"
                          value={season.description || ''}
                          onChange={(e) => updateSeasonalRate(index, 'description', e.target.value)}
                          placeholder="Season name (e.g., Summer)"
                          className="text-sm font-medium bg-transparent border-b border-gray-300 focus:outline-none focus:border-yellow-500"
                        />
                        <button
                          onClick={() => removeSeasonalRate(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="text-xs text-gray-600">Start Month</label>
                          <select
                            value={season.start_month}
                            onChange={(e) => updateSeasonalRate(index, 'start_month', parseInt(e.target.value))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-yellow-500"
                          >
                            {monthNames.map((month, i) => (
                              <option key={i} value={i + 1}>{month}</option>
                            ))}
                          </select>
                        </div>
                        
                        <div>
                          <label className="text-xs text-gray-600">End Month</label>
                          <select
                            value={season.end_month}
                            onChange={(e) => updateSeasonalRate(index, 'end_month', parseInt(e.target.value))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-yellow-500"
                          >
                            {monthNames.map((month, i) => (
                              <option key={i} value={i + 1}>{month}</option>
                            ))}
                          </select>
                        </div>
                        
                        <div>
                          <label className="text-xs text-gray-600">Base Rate ($/kWh) {formData.rate_type === 'seasonal_tiered' && '(Optional)'}</label>
                          <input
                            type="number"
                            step="0.001"
                            value={season.base_rate || ''}
                            onChange={(e) => updateSeasonalRate(index, 'base_rate', e.target.value ? parseFloat(e.target.value) : 0)}
                            placeholder={formData.rate_type === 'seasonal_tiered' ? 'Optional' : 'Required'}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-yellow-500"
                          />
                        </div>
                      </div>

                      {/* Tier rates for seasonal_tiered */}
                      {formData.rate_type === 'seasonal_tiered' && (
                        <div className="mt-3 bg-yellow-100 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="text-sm font-semibold">Season Tiers</h5>
                            <button
                              type="button"
                              onClick={() => addSeasonTier(index)}
                              className="flex items-center space-x-1 px-2 py-1 bg-yellow-600 text-white text-xs rounded hover:bg-yellow-700"
                            >
                              <Plus className="h-3 w-3" />
                              <span>Add Tier</span>
                            </button>
                          </div>
                          
                          {season.tier_rates && season.tier_rates.length > 0 ? (
                            <div className="space-y-2">
                              {season.tier_rates.map((tier, tierIndex) => (
                                <div key={tierIndex} className="bg-white rounded p-2 border border-yellow-300">
                                  <div className="flex items-center justify-between mb-1">
                                    <input
                                      type="text"
                                      value={tier.description || `Tier ${tierIndex + 1}`}
                                      onChange={(e) => updateSeasonTier(index, tierIndex, 'description', e.target.value)}
                                      className="text-xs font-medium bg-transparent border-b border-gray-300 focus:outline-none focus:border-yellow-600"
                                    />
                                    <button
                                      type="button"
                                      onClick={() => removeSeasonTier(index, tierIndex)}
                                      className="text-red-500 hover:text-red-700"
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </button>
                                  </div>
                                  
                                  <div className="grid grid-cols-3 gap-2">
                                    <div>
                                      <label className="text-xs text-gray-600">Min kWh</label>
                                      <input
                                        type="number"
                                        step="1"
                                        value={tier.min_kwh || 0}
                                        onChange={(e) => updateSeasonTier(index, tierIndex, 'min_kwh', parseFloat(e.target.value) || 0)}
                                        className="w-full px-1 py-0.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-yellow-500"
                                        disabled={tierIndex > 0}
                                      />
                                    </div>
                                    
                                    <div>
                                      <label className="text-xs text-gray-600">Max kWh</label>
                                      <input
                                        type="number"
                                        step="1"
                                        value={tier.max_kwh || ''}
                                        onChange={(e) => {
                                          updateSeasonTier(index, tierIndex, 'max_kwh', e.target.value ? parseFloat(e.target.value) : undefined)
                                          // Auto-update next tier's min if exists
                                          if (e.target.value && tierIndex < season.tier_rates!.length - 1) {
                                            updateSeasonTier(index, tierIndex + 1, 'min_kwh', parseFloat(e.target.value))
                                          }
                                        }}
                                        placeholder="∞"
                                        className="w-full px-1 py-0.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-yellow-500"
                                      />
                                    </div>
                                    
                                    <div>
                                      <label className="text-xs text-gray-600">Rate</label>
                                      <input
                                        type="number"
                                        step="0.001"
                                        value={tier.rate_per_kwh}
                                        onChange={(e) => updateSeasonTier(index, tierIndex, 'rate_per_kwh', parseFloat(e.target.value))}
                                        className="w-full px-1 py-0.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-yellow-500"
                                      />
                                    </div>
                                  </div>
                                  
                                  <div className="text-xs text-gray-500 mt-1">
                                    Range: {tier.min_kwh || 0} - {tier.max_kwh || 'Unlimited'} kWh @ ${tier.rate_per_kwh}/kWh
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-gray-500">No tiers for this season. Click "Add Tier" to start.</p>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Additional Charges */}
          <div className="bg-purple-50 rounded-lg p-4">
            <h4 className="font-semibold mb-3">Additional Charges & Fees</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Monthly Service Charge ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.monthly_service_charge}
                  onChange={(e) => setFormData({ ...formData, monthly_service_charge: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Demand Charge ($/kW)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.demand_charge_per_kw}
                  onChange={(e) => setFormData({ ...formData, demand_charge_per_kw: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tax Rate (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.tax_rate}
                  onChange={(e) => setFormData({ ...formData, tax_rate: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
                />
              </div>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              placeholder="Any additional notes about this rate structure..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
            />
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <Info className="h-5 w-5 text-blue-500 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-semibold mb-1">Rate Structure Tips:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li><strong>Flat Rate:</strong> Best for simple billing with one rate for all usage</li>
                  <li><strong>Time-of-Use:</strong> Different rates for peak/off-peak hours</li>
                  <li><strong>Tiered:</strong> Rates increase with higher usage levels</li>
                  <li><strong>Seasonal:</strong> Different rates for summer/winter months</li>
                  <li><strong>TOU + Tiered:</strong> Time-based rates with usage tiers</li>
                  <li><strong>Seasonal + Tiered:</strong> Each season has its own tier structure</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6">
          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className={`
                flex items-center space-x-2 px-4 py-2 rounded-lg font-medium
                ${saving 
                  ? 'bg-gray-300 cursor-not-allowed' 
                  : 'bg-kasa-primary hover:bg-kasa-secondary text-white'}
              `}
            >
              <Save className="h-5 w-5" />
              <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
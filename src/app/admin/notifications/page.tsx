'use client';

import React, { useState, useEffect } from 'react';
import { Bell, Mail, MessageSquare, Send, Webhook, Smartphone, TestTube, Save, Plus, Trash2, Edit2 } from 'lucide-react';
import { AppLayout } from '@/components/app-layout';

interface NotificationChannel {
  id: string;
  type: 'email' | 'sms' | 'webhook' | 'slack' | 'discord' | 'push';
  name: string;
  enabled: boolean;
  config: any;
  test_status?: 'success' | 'failure' | 'pending';
  last_used?: string;
}

export default function NotificationSettingsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>('email');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);
  const [testingChannel, setTestingChannel] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  // Email configuration state
  const [emailConfig, setEmailConfig] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_email: '',
    from_name: 'Kasa Monitor',
    use_tls: true,
    use_ssl: false
  });

  // SMS configuration state  
  const [smsConfig, setSmsConfig] = useState({
    provider: 'twilio',
    twilio_account_sid: '',
    twilio_auth_token: '',
    twilio_from_number: '',
    aws_sns_region: '',
    aws_sns_access_key: '',
    aws_sns_secret_key: ''
  });

  // Webhook configuration state
  const [webhookConfig, setWebhookConfig] = useState({
    url: '',
    method: 'POST',
    headers: {} as Record<string, string>,
    auth_type: 'none',
    auth_username: '',
    auth_password: '',
    auth_token: '',
    secret: '',
    retry_count: 3,
    timeout: 30
  });

  // Slack configuration state
  const [slackConfig, setSlackConfig] = useState({
    webhook_url: '',
    channel: '',
    username: 'Kasa Monitor',
    icon_emoji: ':electric_plug:',
    mention_users: [] as string[],
    oauth_token: ''
  });

  // Discord configuration state
  const [discordConfig, setDiscordConfig] = useState({
    webhook_url: '',
    username: 'Kasa Monitor',
    avatar_url: '',
    embed_color: '#0099ff',
    mention_roles: [] as string[],
    mention_users: [] as string[]
  });

  // Push notification configuration state
  const [pushConfig, setPushConfig] = useState({
    vapid_public_key: '',
    vapid_private_key: '',
    vapid_email: '',
    fcm_server_key: '',
    apns_cert_path: '',
    apns_key_path: '',
    apns_team_id: '',
    apns_key_id: ''
  });

  useEffect(() => {
    fetchChannels();
    loadConfigurations();
  }, []);

  const fetchChannels = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/notification-channels', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setChannels(data);
      }
    } catch (error) {
      console.error('Failed to fetch notification channels:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadConfigurations = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/notification-channels/config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.email) setEmailConfig(data.email);
        if (data.sms) setSmsConfig(data.sms);
        if (data.webhook) setWebhookConfig(data.webhook);
        if (data.slack) setSlackConfig(data.slack);
        if (data.discord) setDiscordConfig(data.discord);
        if (data.push) setPushConfig(data.push);
      }
    } catch (error) {
      console.error('Failed to load configurations:', error);
    }
  };

  const saveConfiguration = async (type: string) => {
    setSaveStatus('saving');
    
    const configs: Record<string, any> = {
      email: emailConfig,
      sms: smsConfig,
      webhook: webhookConfig,
      slack: slackConfig,
      discord: discordConfig,
      push: pushConfig
    };

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/notification-channels/${type}/config`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(configs[type])
      });
      
      if (response.ok) {
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch (error) {
      console.error('Failed to save configuration:', error);
      setSaveStatus('error');
    }
  };

  const testChannel = async (channelId: string, type: string) => {
    setTestingChannel(channelId);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/notification-channels/${type}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          channelId,
          testMessage: 'This is a test notification from Kasa Monitor'
        })
      });
      
      if (response.ok) {
        setChannels(prev => prev.map(ch => 
          ch.id === channelId ? { ...ch, test_status: 'success' } : ch
        ));
      } else {
        setChannels(prev => prev.map(ch => 
          ch.id === channelId ? { ...ch, test_status: 'failure' } : ch
        ));
      }
    } catch (error) {
      console.error('Failed to test channel:', error);
      setChannels(prev => prev.map(ch => 
        ch.id === channelId ? { ...ch, test_status: 'failure' } : ch
      ));
    } finally {
      setTestingChannel(null);
    }
  };

  const getTabIcon = (type: string) => {
    switch (type) {
      case 'email': return <Mail className="h-4 w-4" />;
      case 'sms': return <MessageSquare className="h-4 w-4" />;
      case 'webhook': return <Webhook className="h-4 w-4" />;
      case 'slack': return <Send className="h-4 w-4" />;
      case 'discord': return <MessageSquare className="h-4 w-4" />;
      case 'push': return <Smartphone className="h-4 w-4" />;
      default: return <Bell className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Notification Settings</h1>
          <p className="text-gray-600 mt-1">Configure notification channels for alerts and system events</p>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              {['email', 'sms', 'webhook', 'slack', 'discord', 'push'].map((type) => (
                <button
                  key={type}
                  onClick={() => setActiveTab(type)}
                  className={`py-2 px-6 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                    activeTab === type
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {getTabIcon(type)}
                  <span className="capitalize">{type}</span>
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {/* Email Configuration */}
            {activeTab === 'email' && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Email Configuration (SMTP)</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Host
                    </label>
                    <input
                      type="text"
                      value={emailConfig.smtp_host}
                      onChange={(e) => setEmailConfig({...emailConfig, smtp_host: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="smtp.gmail.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Port
                    </label>
                    <input
                      type="number"
                      value={emailConfig.smtp_port}
                      onChange={(e) => setEmailConfig({...emailConfig, smtp_port: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="587"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      value={emailConfig.smtp_username}
                      onChange={(e) => setEmailConfig({...emailConfig, smtp_username: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="your-email@gmail.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      value={emailConfig.smtp_password}
                      onChange={(e) => setEmailConfig({...emailConfig, smtp_password: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="••••••••"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      From Email
                    </label>
                    <input
                      type="email"
                      value={emailConfig.from_email}
                      onChange={(e) => setEmailConfig({...emailConfig, from_email: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="noreply@yourdomain.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      From Name
                    </label>
                    <input
                      type="text"
                      value={emailConfig.from_name}
                      onChange={(e) => setEmailConfig({...emailConfig, from_name: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Kasa Monitor"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={emailConfig.use_tls}
                      onChange={(e) => setEmailConfig({...emailConfig, use_tls: e.target.checked})}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Use TLS</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={emailConfig.use_ssl}
                      onChange={(e) => setEmailConfig({...emailConfig, use_ssl: e.target.checked})}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Use SSL</span>
                  </label>
                </div>

                <div className="flex justify-between items-center pt-4">
                  <button
                    onClick={() => testChannel('email-default', 'email')}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center"
                  >
                    <TestTube className="h-4 w-4 mr-2" />
                    Test Connection
                  </button>
                  
                  <button
                    onClick={() => saveConfiguration('email')}
                    disabled={saveStatus === 'saving'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}

            {/* SMS Configuration */}
            {activeTab === 'sms' && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">SMS Configuration</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    SMS Provider
                  </label>
                  <select
                    value={smsConfig.provider}
                    onChange={(e) => setSmsConfig({...smsConfig, provider: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="twilio">Twilio</option>
                    <option value="aws_sns">AWS SNS</option>
                    <option value="messagebird">MessageBird</option>
                    <option value="vonage">Vonage (Nexmo)</option>
                  </select>
                </div>

                {smsConfig.provider === 'twilio' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Account SID
                      </label>
                      <input
                        type="text"
                        value={smsConfig.twilio_account_sid}
                        onChange={(e) => setSmsConfig({...smsConfig, twilio_account_sid: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="ACxxxxxxxxxxxxxxxxx"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Auth Token
                      </label>
                      <input
                        type="password"
                        value={smsConfig.twilio_auth_token}
                        onChange={(e) => setSmsConfig({...smsConfig, twilio_auth_token: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="••••••••"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        From Phone Number
                      </label>
                      <input
                        type="tel"
                        value={smsConfig.twilio_from_number}
                        onChange={(e) => setSmsConfig({...smsConfig, twilio_from_number: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="+1234567890"
                      />
                    </div>
                  </div>
                )}

                <div className="flex justify-between items-center pt-4">
                  <button
                    onClick={() => testChannel('sms-default', 'sms')}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center"
                  >
                    <TestTube className="h-4 w-4 mr-2" />
                    Test Connection
                  </button>
                  
                  <button
                    onClick={() => saveConfiguration('sms')}
                    disabled={saveStatus === 'saving'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}

            {/* Webhook Configuration */}
            {activeTab === 'webhook' && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Webhook Configuration</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Webhook URL
                  </label>
                  <input
                    type="url"
                    value={webhookConfig.url}
                    onChange={(e) => setWebhookConfig({...webhookConfig, url: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://your-webhook-endpoint.com/notifications"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      HTTP Method
                    </label>
                    <select
                      value={webhookConfig.method}
                      onChange={(e) => setWebhookConfig({...webhookConfig, method: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                      <option value="PATCH">PATCH</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Authentication Type
                    </label>
                    <select
                      value={webhookConfig.auth_type}
                      onChange={(e) => setWebhookConfig({...webhookConfig, auth_type: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="none">None</option>
                      <option value="basic">Basic Auth</option>
                      <option value="bearer">Bearer Token</option>
                      <option value="hmac">HMAC Signature</option>
                    </select>
                  </div>
                </div>

                {webhookConfig.auth_type === 'bearer' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bearer Token
                    </label>
                    <input
                      type="password"
                      value={webhookConfig.auth_token}
                      onChange={(e) => setWebhookConfig({...webhookConfig, auth_token: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="your-bearer-token"
                    />
                  </div>
                )}

                {webhookConfig.auth_type === 'hmac' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      HMAC Secret
                    </label>
                    <input
                      type="password"
                      value={webhookConfig.secret}
                      onChange={(e) => setWebhookConfig({...webhookConfig, secret: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="your-hmac-secret"
                    />
                  </div>
                )}

                <div className="flex justify-between items-center pt-4">
                  <button
                    onClick={() => testChannel('webhook-default', 'webhook')}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center"
                  >
                    <TestTube className="h-4 w-4 mr-2" />
                    Test Webhook
                  </button>
                  
                  <button
                    onClick={() => saveConfiguration('webhook')}
                    disabled={saveStatus === 'saving'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}

            {/* Slack Configuration */}
            {activeTab === 'slack' && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Slack Configuration</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Webhook URL
                  </label>
                  <input
                    type="url"
                    value={slackConfig.webhook_url}
                    onChange={(e) => setSlackConfig({...slackConfig, webhook_url: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Get this from your Slack app's Incoming Webhooks
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Channel
                    </label>
                    <input
                      type="text"
                      value={slackConfig.channel}
                      onChange={(e) => setSlackConfig({...slackConfig, channel: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="#alerts or @username"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bot Username
                    </label>
                    <input
                      type="text"
                      value={slackConfig.username}
                      onChange={(e) => setSlackConfig({...slackConfig, username: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Kasa Monitor"
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4">
                  <button
                    onClick={() => testChannel('slack-default', 'slack')}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center"
                  >
                    <TestTube className="h-4 w-4 mr-2" />
                    Send Test Message
                  </button>
                  
                  <button
                    onClick={() => saveConfiguration('slack')}
                    disabled={saveStatus === 'saving'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}

            {/* Discord Configuration */}
            {activeTab === 'discord' && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Discord Configuration</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Webhook URL
                  </label>
                  <input
                    type="url"
                    value={discordConfig.webhook_url}
                    onChange={(e) => setDiscordConfig({...discordConfig, webhook_url: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://discord.com/api/webhooks/..."
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Get this from Server Settings → Integrations → Webhooks
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bot Username
                    </label>
                    <input
                      type="text"
                      value={discordConfig.username}
                      onChange={(e) => setDiscordConfig({...discordConfig, username: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Kasa Monitor"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Embed Color
                    </label>
                    <input
                      type="text"
                      value={discordConfig.embed_color}
                      onChange={(e) => setDiscordConfig({...discordConfig, embed_color: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="#0099ff"
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4">
                  <button
                    onClick={() => testChannel('discord-default', 'discord')}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center"
                  >
                    <TestTube className="h-4 w-4 mr-2" />
                    Send Test Message
                  </button>
                  
                  <button
                    onClick={() => saveConfiguration('discord')}
                    disabled={saveStatus === 'saving'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}

            {/* Push Notifications Configuration */}
            {activeTab === 'push' && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Push Notifications Configuration</h3>
                
                <div className="border-l-4 border-blue-400 bg-blue-50 p-4 mb-4">
                  <div className="flex">
                    <div className="ml-3">
                      <p className="text-sm text-blue-700">
                        Push notifications require additional setup for each platform. 
                        Web push uses VAPID keys, iOS uses APNS, and Android uses FCM.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Web Push (VAPID)</h4>
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        VAPID Public Key
                      </label>
                      <input
                        type="text"
                        value={pushConfig.vapid_public_key}
                        onChange={(e) => setPushConfig({...pushConfig, vapid_public_key: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Your VAPID public key"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        VAPID Private Key
                      </label>
                      <input
                        type="password"
                        value={pushConfig.vapid_private_key}
                        onChange={(e) => setPushConfig({...pushConfig, vapid_private_key: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Your VAPID private key"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4">
                  <button
                    onClick={() => testChannel('push-default', 'push')}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 flex items-center"
                  >
                    <TestTube className="h-4 w-4 mr-2" />
                    Test Push
                  </button>
                  
                  <button
                    onClick={() => saveConfiguration('push')}
                    disabled={saveStatus === 'saving'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}

            {/* Save Status Messages */}
            {saveStatus === 'saved' && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-600">Configuration saved successfully!</p>
              </div>
            )}

            {saveStatus === 'error' && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-600">Failed to save configuration. Please try again.</p>
              </div>
            )}
          </div>
        </div>

        {/* Information Panel */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-900 mb-4">Configuration Help</h3>
          <div className="space-y-3 text-sm text-blue-800">
            <div>
              <strong>Email:</strong> Configure SMTP settings for email notifications. Gmail users should use app-specific passwords.
            </div>
            <div>
              <strong>SMS:</strong> Requires a third-party SMS provider account (Twilio, AWS SNS, etc.).
            </div>
            <div>
              <strong>Webhook:</strong> Send notifications to any HTTP endpoint with customizable authentication.
            </div>
            <div>
              <strong>Slack:</strong> Create an incoming webhook in your Slack workspace settings.
            </div>
            <div>
              <strong>Discord:</strong> Create a webhook in your Discord server settings under Integrations.
            </div>
            <div>
              <strong>Push:</strong> Browser and mobile push notifications require platform-specific setup.
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
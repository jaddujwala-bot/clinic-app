// Preload script - securely exposes the API to the renderer via contextBridge
const { contextBridge, ipcRenderer } = require('electron');

// Helper to invoke an IPC channel and unwrap { ok, data, error }
const invoke = async (channel, ...args) => {
  const res = await ipcRenderer.invoke(channel, ...args);
  if (res && res.ok) return res.data;
  throw new Error(res?.error || 'Unknown IPC error');
};

// The `clinicAPI` object becomes available as window.clinicAPI in React
contextBridge.exposeInMainWorld('clinicAPI', {
  patients: {
    list: (params) => invoke('patients:list', params),
    get: (id) => invoke('patients:get', id),
    create: (data) => invoke('patients:create', data),
    update: (id, data) => invoke('patients:update', id, data),
    remove: (id) => invoke('patients:remove', id),
  },
  doctors: {
    list: (params) => invoke('doctors:list', params),
    get: (id) => invoke('doctors:get', id),
    create: (data) => invoke('doctors:create', data),
    update: (id, data) => invoke('doctors:update', id, data),
    remove: (id) => invoke('doctors:remove', id),
  },
  appointments: {
    list: (params) => invoke('appointments:list', params),
    get: (id) => invoke('appointments:get', id),
    create: (data) => invoke('appointments:create', data),
    update: (id, data) => invoke('appointments:update', id, data),
    setStatus: (id, status) => invoke('appointments:setStatus', id, status),
    remove: (id) => invoke('appointments:remove', id),
  },
  medicines: {
    list: (params) => invoke('medicines:list', params),
    get: (id) => invoke('medicines:get', id),
    create: (data) => invoke('medicines:create', data),
    update: (id, data) => invoke('medicines:update', id, data),
    remove: (id) => invoke('medicines:remove', id),
  },
  pharmacy: {
    dispense: (data) => invoke('pharmacy:dispense', data),
    transactions: (params) => invoke('pharmacy:transactions', params),
  },
  billing: {
    list: (params) => invoke('billing:list', params),
    get: (id) => invoke('billing:get', id),
    create: (data) => invoke('billing:create', data),
    update: (id, data) => invoke('billing:update', id, data),
    pay: (id, amount) => invoke('billing:pay', id, amount),
    remove: (id) => invoke('billing:remove', id),
    summary: (params) => invoke('billing:summary', params),
  },
  visits: {
    list: (params) => invoke('visits:list', params),
    get: (id) => invoke('visits:get', id),
    create: (data) => invoke('visits:create', data),
    update: (id, data) => invoke('visits:update', id, data),
    remove: (id) => invoke('visits:remove', id),
  },
  prescriptions: {
    list: (params) => invoke('prescriptions:list', params),
    create: (data) => invoke('prescriptions:create', data),
    setStatus: (id, status) => invoke('prescriptions:setStatus', id, status),
    remove: (id) => invoke('prescriptions:remove', id),
  },
  reports: {
    overview: () => invoke('reports:overview'),
    patients: (params) => invoke('reports:patients', params),
    doctors: () => invoke('reports:doctors'),
    pharmacy: (params) => invoke('reports:pharmacy', params),
  },
});

// IPC Handlers - bridges renderer (React) requests to service layer
// Registered in the Electron main process. Each channel maps to a service method.
const { ipcMain } = require('electron');

const { PatientService } = require('../renderer/clinic-center/src/api/patients/patients.service');
const { DoctorService } = require('../renderer/clinic-center/src/api/doctors/doctors.service');
const { AppointmentService } = require('../renderer/clinic-center/src/api/appointments/appointments.service');
const { PharmacyService } = require('../renderer/clinic-center/src/api/pharmacy/pharmacy.service');
const { BillingService } = require('../renderer/clinic-center/src/api/billing/billing.service');
const { VisitService, PrescriptionService } = require('../renderer/clinic-center/src/api/visits/visits.service');
const { ReportsService } = require('../renderer/clinic-center/src/api/reports/reports.service');

// Wrap a handler so errors are returned as { error } instead of crashing IPC
function safe(fn) {
  return async (_event, ...args) => {
    try {
      const data = await fn(...args);
      return { ok: true, data };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  };
}

function registerIpcHandlers() {
  // ---- Patients ----
  ipcMain.handle('patients:list', safe((params) => PatientService.list(params)));
  ipcMain.handle('patients:get', safe((id) => PatientService.getById(id)));
  ipcMain.handle('patients:create', safe((data) => PatientService.create(data)));
  ipcMain.handle('patients:update', safe((id, data) => PatientService.update(id, data)));
  ipcMain.handle('patients:remove', safe((id) => PatientService.remove(id)));

  // ---- Doctors ----
  ipcMain.handle('doctors:list', safe((params) => DoctorService.list(params)));
  ipcMain.handle('doctors:get', safe((id) => DoctorService.getById(id)));
  ipcMain.handle('doctors:create', safe((data) => DoctorService.create(data)));
  ipcMain.handle('doctors:update', safe((id, data) => DoctorService.update(id, data)));
  ipcMain.handle('doctors:remove', safe((id) => DoctorService.remove(id)));

  // ---- Appointments ----
  ipcMain.handle('appointments:list', safe((params) => AppointmentService.list(params)));
  ipcMain.handle('appointments:get', safe((id) => AppointmentService.getById(id)));
  ipcMain.handle('appointments:create', safe((data) => AppointmentService.create(data)));
  ipcMain.handle('appointments:update', safe((id, data) => AppointmentService.update(id, data)));
  ipcMain.handle('appointments:setStatus', safe((id, status) => AppointmentService.setStatus(id, status)));
  ipcMain.handle('appointments:remove', safe((id) => AppointmentService.remove(id)));

  // ---- Pharmacy: Medicines ----
  ipcMain.handle('medicines:list', safe((params) => PharmacyService.listMedicines(params)));
  ipcMain.handle('medicines:get', safe((id) => PharmacyService.getMedicine(id)));
  ipcMain.handle('medicines:create', safe((data) => PharmacyService.createMedicine(data)));
  ipcMain.handle('medicines:update', safe((id, data) => PharmacyService.updateMedicine(id, data)));
  ipcMain.handle('medicines:remove', safe((id) => PharmacyService.removeMedicine(id)));

  // ---- Pharmacy: Dispensing ----
  ipcMain.handle('pharmacy:dispense', safe((data) => PharmacyService.dispense(data)));
  ipcMain.handle('pharmacy:transactions', safe((params) => PharmacyService.listTransactions(params)));

  // ---- Billing ----
  ipcMain.handle('billing:list', safe((params) => BillingService.list(params)));
  ipcMain.handle('billing:get', safe((id) => BillingService.getById(id)));
  ipcMain.handle('billing:create', safe((data) => BillingService.create(data)));
  ipcMain.handle('billing:update', safe((id, data) => BillingService.update(id, data)));
  ipcMain.handle('billing:pay', safe((id, amount) => BillingService.recordPayment(id, amount)));
  ipcMain.handle('billing:remove', safe((id) => BillingService.remove(id)));
  ipcMain.handle('billing:summary', safe((params) => BillingService.summary(params)));

  // ---- Visits ----
  ipcMain.handle('visits:list', safe((params) => VisitService.list(params)));
  ipcMain.handle('visits:get', safe((id) => VisitService.getById(id)));
  ipcMain.handle('visits:create', safe((data) => VisitService.create(data)));
  ipcMain.handle('visits:update', safe((id, data) => VisitService.update(id, data)));
  ipcMain.handle('visits:remove', safe((id) => VisitService.remove(id)));

  // ---- Prescriptions ----
  ipcMain.handle('prescriptions:list', safe((params) => PrescriptionService.list(params)));
  ipcMain.handle('prescriptions:create', safe((data) => PrescriptionService.create(data)));
  ipcMain.handle('prescriptions:setStatus', safe((id, status) => PrescriptionService.setStatus(id, status)));
  ipcMain.handle('prescriptions:remove', safe((id) => PrescriptionService.remove(id)));

  // ---- Reports ----
  ipcMain.handle('reports:overview', safe(() => ReportsService.overview()));
  ipcMain.handle('reports:patients', safe((params) => ReportsService.patientReport(params)));
  ipcMain.handle('reports:doctors', safe(() => ReportsService.doctorReport()));
  ipcMain.handle('reports:pharmacy', safe((params) => ReportsService.pharmacyReport(params)));
}

module.exports = { registerIpcHandlers };

import requests
import json
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

class ParkingExitApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parking Exit System - RSI BNA")
        self.root.geometry("800x600")
        
        # API Configuration
        self.base_url = "http://192.168.2.6:5051/api"
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create widgets
        self.create_widgets()
        
    def create_widgets(self):
        # Ticket Entry
        ttk.Label(self.main_frame, text="Nomor Tiket:").grid(row=0, column=0, padx=5, pady=5)
        self.ticket_entry = ttk.Entry(self.main_frame, width=30)
        self.ticket_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # License Plate Entry
        ttk.Label(self.main_frame, text="Plat Nomor:").grid(row=1, column=0, padx=5, pady=5)
        self.plate_entry = ttk.Entry(self.main_frame, width=30)
        self.plate_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Buttons
        ttk.Button(self.main_frame, text="Cek Tiket", command=self.check_ticket).grid(row=2, column=0, padx=5, pady=10)
        ttk.Button(self.main_frame, text="Proses Keluar", command=self.process_exit).grid(row=2, column=1, padx=5, pady=10)
        
        # Information Display
        self.info_frame = ttk.LabelFrame(self.main_frame, text="Informasi Parkir", padding="10")
        self.info_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Info Labels
        self.create_info_labels()
        
    def create_info_labels(self):
        self.info_labels = {}
        info_fields = [
            "Status", "Waktu Masuk", "Durasi", "Jenis Kendaraan",
            "Estimasi Biaya", "Status Pembayaran"
        ]
        
        for idx, field in enumerate(info_fields):
            ttk.Label(self.info_frame, text=f"{field}:").grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            self.info_labels[field] = ttk.Label(self.info_frame, text="-")
            self.info_labels[field].grid(row=idx, column=1, sticky=tk.W, padx=5, pady=2)
    
    def check_ticket(self):
        ticket = self.ticket_entry.get().strip()
        if not ticket:
            messagebox.showerror("Error", "Masukkan nomor tiket!")
            return
            
        try:
            response = requests.get(
                f"{self.base_url}/cek-tiket",
                params={"tiket": ticket, "plat": self.plate_entry.get().strip()}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    self.update_info_display(data["data"])
                else:
                    messagebox.showerror("Error", data.get("message", "Gagal mengecek tiket"))
            else:
                messagebox.showerror("Error", "Gagal terhubung ke server")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Kesalahan koneksi: {str(e)}")
    
    def process_exit(self):
        ticket = self.ticket_entry.get().strip()
        if not ticket:
            messagebox.showerror("Error", "Masukkan nomor tiket!")
            return
            
        try:
            response = requests.post(
                f"{self.base_url}/keluar",
                json={
                    "tiket": ticket,
                    "plat": self.plate_entry.get().strip()
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    self.show_exit_success(data["data"])
                else:
                    messagebox.showerror("Error", data.get("message", "Gagal memproses keluar"))
            else:
                messagebox.showerror("Error", "Gagal terhubung ke server")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Kesalahan koneksi: {str(e)}")
    
    def update_info_display(self, data):
        self.info_labels["Status"].config(text="Aktif" if data["status"]["is_valid"] else "Tidak Valid")
        self.info_labels["Waktu Masuk"].config(text=data["waktu_masuk"])
        self.info_labels["Durasi"].config(text=data["durasi_current"])
        self.info_labels["Jenis Kendaraan"].config(text=data["jenis"])
        self.info_labels["Estimasi Biaya"].config(text=f"Rp {data['estimasi_biaya']:,}")
        self.info_labels["Status Pembayaran"].config(
            text="Sudah Dibayar" if data["status"]["is_paid"] else "Belum Dibayar"
        )
    
    def show_exit_success(self, data):
        success_text = f"""
        Kendaraan berhasil keluar!
        
        Tiket: {data['tiket']}
        Plat: {data['plat']}
        Waktu Masuk: {data['waktu_masuk']}
        Waktu Keluar: {data['waktu_keluar']}
        Durasi: {data['durasi']}
        Tarif: Rp {data['tarif']:,}
        """
        messagebox.showinfo("Sukses", success_text)
        self.clear_entries()
    
    def clear_entries(self):
        self.ticket_entry.delete(0, tk.END)
        self.plate_entry.delete(0, tk.END)
        for label in self.info_labels.values():
            label.config(text="-")

if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingExitApp(root)
    root.mainloop() 
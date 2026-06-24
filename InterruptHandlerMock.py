import sys
import csv
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QLabel, QPushButton, QComboBox, QSlider, 
                             QGridLayout, QProgressBar, QScrollArea, QTextEdit, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class ModernDashboard(QWidget):
    def __init__(self):
        super().__init__()
        # Data Storage
        self.tasks = [] 
        self.current_task_index = 0
        self.is_running = False
        self.current_algo = "FCFS"
        self.time_quantum = 1000 
        
        # Context Switching State
        self.is_switching = False
        self.last_task_id = None
        
        # Timer for Simulation
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.run_simulation_step)
        
        self.setWindowTitle("Interrupt Mock Handler")
        self.setMinimumSize(1100, 900)
        self.setStyleSheet("background-color: #121926; color: white; font-family: 'Segoe UI';")
        self.initUI()

    def create_card(self, title):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 10px;
                border: 1px solid #334155;
            }
            QLabel { border: none; font-weight: bold; }
        """)
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet("color: #94a3b8; font-size: 14px;")
        layout.addWidget(label)
        return card, layout

    def initUI(self):
        outer_layout = QVBoxLayout(self)
        main_content_layout = QHBoxLayout()

        # --- LEFT SIDE COLUMN ---
        left_column = QVBoxLayout()
        
        # 1. Add Task Section
        add_task_card, at_layout = self.create_card("Add Task / Interrupt")
        input_layout = QHBoxLayout()
        self.inputs = {} 
        for placeholder in ["Duration", "Type", "Priority", "Category"]:
            cb = QComboBox()
            if placeholder == "Duration":
                cb.addItems(["500", "1000", "2000", "5000"])
            elif placeholder == "Type":
                cb.addItems(["Task", "Interrupt"])
            elif placeholder == "Priority":
                cb.addItems(["Low", "Medium", "High"])
            else:
                cb.addItems(["CPU-bound", "I/O-bound"])
            cb.setStyleSheet("background-color: #0f172a; padding: 5px; border-radius: 5px; border: 1px solid #334155;")
            input_layout.addWidget(cb)
            self.inputs[placeholder] = cb
        
        add_btn = QPushButton("+ Add")
        add_btn.setStyleSheet("background-color: #38bdf8; color: black; font-weight: bold; padding: 8px; border-radius: 5px;")
        add_btn.clicked.connect(self.add_task_logic)
        input_layout.addWidget(add_btn)
        at_layout.addLayout(input_layout)
        left_column.addWidget(add_task_card)

        # 2. Simulation Control
        sim_ctrl_card, sc_layout = self.create_card("Simulation Control")
        sc_buttons = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setStyleSheet("background-color: #22c55e; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        self.start_btn.clicked.connect(self.toggle_simulation)
        sc_buttons.addWidget(self.start_btn)
        
        reset_btn = QPushButton("↺ Reset")
        reset_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        reset_btn.clicked.connect(self.reset_simulation)
        sc_buttons.addWidget(reset_btn)

        

        sc_layout.addLayout(sc_buttons)
        left_column.addWidget(sim_ctrl_card)

        # 3. Simulation Speed
        speed_card, sp_layout = self.create_card("Simulation Speed")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(100, 2000)
        self.speed_slider.setValue(1000)
        sp_layout.addWidget(self.speed_slider)
        left_column.addWidget(speed_card)

        # 4. Queue Visualization
        queue_card, q_layout = self.create_card("Queue Visualization")
        self.q_container_layout = QHBoxLayout() 
        self.queue_layouts = {} 
        for name, color in [("Interrupt Queue", "#451a1a"), ("Ready Queue", "#1e1b4b"), ("Completed", "#064e3b")]:
            parent_frame = QFrame()
            parent_frame.setMinimumHeight(100)
            parent_frame.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: 1px dashed #ffffff22;")
            v_layout = QVBoxLayout(parent_frame)
            v_layout.addWidget(QLabel(name), alignment=Qt.AlignTop)
            boxes_area = QHBoxLayout()
            v_layout.addLayout(boxes_area)
            self.queue_layouts[name] = boxes_area
            self.q_container_layout.addWidget(parent_frame)
        q_layout.addLayout(self.q_container_layout)
        left_column.addWidget(queue_card)

        # 5. Gantt Chart Timeline
        gantt_card, g_layout = self.create_card("Gantt Chart Timeline")
        gantt_scroll = QScrollArea()
        gantt_scroll.setWidgetResizable(True)
        gantt_scroll.setStyleSheet("background: #0f172a; border: none;")
        self.gantt_content = QFrame()
        self.g_inner_layout = QHBoxLayout(self.gantt_content)
        self.g_inner_layout.setAlignment(Qt.AlignLeft)
        gantt_scroll.setWidget(self.gantt_content)
        g_layout.addWidget(gantt_scroll)
        left_column.addWidget(gantt_card)

        main_content_layout.addLayout(left_column, 3)

        # --- RIGHT SIDE COLUMN ---
        right_column = QVBoxLayout()
        
        # CPU Activity
        cpu_card, cpu_layout = self.create_card("CPU Activity")
        self.cpu_circle = QLabel("IDLE")
        self.cpu_circle.setAlignment(Qt.AlignCenter)
        self.cpu_circle.setStyleSheet("border: 6px solid #22c55e; border-radius: 65px; min-width: 130px; min-height: 130px; color: #22c55e; font-weight: bold;")
        cpu_layout.addWidget(self.cpu_circle, alignment=Qt.AlignCenter)
        right_column.addWidget(cpu_card)

        # Statistics
        stats_card, stats_layout = self.create_card("Statistics")
        self.algo_label = QLabel(f"Current Algo: {self.current_algo}")
        self.algo_label.setStyleSheet("color: #38bdf8; font-size: 12px;")
        stats_layout.addWidget(self.algo_label)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar { background-color: #0f172a; height: 10px; border-radius: 5px; } QProgressBar::chunk { background-color: #3b82f6; border-radius: 5px; }")
        stats_layout.addWidget(self.progress)
        right_column.addWidget(stats_card)
        
        # Scheduling Algorithm
        algo_card, algo_layout = self.create_card("Scheduling Algorithm")
        for algo in ["Priority Queue", "FCFS", "Round Robin"]:
            btn = QPushButton(algo)
            btn.setStyleSheet("text-align: left; padding: 8px; background: #0f172a; border: 1px solid #334155; border-radius: 5px;")
            btn.clicked.connect(lambda checked, a=algo: self.set_algorithm(a))
            algo_layout.addWidget(btn)
        right_column.addWidget(algo_card)

        # 6. Pre-configured Scenarios
        scen_card, scen_layout = self.create_card("Pre-configured Scenarios")
        for s_name in ["Balanced Load", "Heavy Load", "Interrupt Storm"]:
            s_btn = QPushButton(s_name)
            s_btn.setStyleSheet("text-align: left; padding: 8px; background: #1e293b; border: 1px solid #475569; border-radius: 5px; color: #38bdf8;")
            s_btn.clicked.connect(lambda checked, s=s_name: self.load_scenario(s))
            scen_layout.addWidget(s_btn)
        right_column.addWidget(scen_card)

        # 7. Export Data
        export_card, ex_layout = self.create_card("Export Data")
        csv_btn = QPushButton("Export as CSV")
        csv_btn.setStyleSheet("padding: 8px; background: #334155; border-radius: 5px;")
        csv_btn.clicked.connect(self.export_to_csv)
        ex_layout.addWidget(csv_btn)
        right_column.addWidget(export_card)

        main_content_layout.addLayout(right_column, 1)
        outer_layout.addLayout(main_content_layout)

        # System Logs
        log_card, log_layout = self.create_card("System Logs")
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #0f172a; border: none; color: #10b981; font-family: 'Consolas';")
        self.log_display.setMaximumHeight(150)
        log_layout.addWidget(self.log_display)
        outer_layout.addWidget(log_card)

    # --- UPDATED SIMULATION STEP WITH PREEMPTION LOGIC ---
    def run_simulation_step(self):
        # Filter only incomplete tasks for scheduling
        active_tasks = [t for t in self.tasks if t["remaining_time"] > 0]
        
        if not active_tasks:
            self.toggle_simulation()
            self.cpu_circle.setText("DONE")
            self.cpu_circle.setStyleSheet("border: 6px solid #22c55e; border-radius: 65px; min-width: 130px; min-height: 130px; color: #22c55e; font-weight: bold;")
            return

        # Check for Priority Preemption before picking task
        if self.current_algo == "Priority Queue":
            p_map = {"High": 0, "Medium": 1, "Low": 2}
            active_tasks.sort(key=lambda x: (0 if x["type"]=="Interrupt" else 1, p_map.get(x["priority"], 3)))
            
            # If current task is no longer the highest priority in queue, preempt it
            highest_task = active_tasks[0]
            if self.last_task_id is not None and self.last_task_id != highest_task['id']:
                self.log_display.append(f"<b>[SYS]:</b> Preempting current task for T{highest_task['id']}...")
                self.is_switching = True # Trigger context switch

        # Pick task (Round Robin handles index internally, FCFS/Priority uses sorted list)
        if self.current_algo == "Round Robin":
            task = self.tasks[self.current_task_index % len(self.tasks)]
            while task["remaining_time"] <= 0:
                self.current_task_index += 1
                task = self.tasks[self.current_task_index % len(self.tasks)]
        else:
            task = active_tasks[0]

        # Visual Context Switch Handler
        if self.last_task_id is not None and self.last_task_id != task['id'] and not self.is_switching:
            self.is_switching = True
            self.cpu_circle.setText("SWITCHING...")
            self.cpu_circle.setStyleSheet("border: 6px solid #f59e0b; border-radius: 65px; min-width: 130px; min-height: 130px; color: #f59e0b; font-weight: bold;")
            return 

        if self.is_switching:
            self.is_switching = False
            self.cpu_circle.setStyleSheet("border: 6px solid #3b82f6; border-radius: 65px; min-width: 130px; min-height: 130px; color: #3b82f6; font-weight: bold;")

        # Execution Logic
        self.last_task_id = task['id']
        exec_slice = self.time_quantum if self.current_algo == "Round Robin" else 500 # Smaller steps for preemption check
        exec_time = min(task["remaining_time"], exec_slice)
        
        task["remaining_time"] -= exec_time
        self.cpu_circle.setText(f"RUNNING\nT{task['id']}\nRem: {task['remaining_time']}")
        self.add_gantt_block(task['id'], task['type'], exec_time)
        
        if task["remaining_time"] <= 0:
            self.log_display.append(f"<b>[LOG]:</b> T{task['id']} completed.")
            if task["widget"]: self.queue_layouts["Completed"].addWidget(task["widget"])
            if self.current_algo == "Round Robin": self.current_task_index += 1
        elif self.current_algo == "Round Robin":
            self.log_display.append(f"<b>[LOG]:</b> T{task['id']} quantum end.")
            self.current_task_index += 1

        # Global Progress
        total_dur = sum(t["duration"] for t in self.tasks)
        total_rem = sum(t["remaining_time"] for t in self.tasks)
        self.progress.setValue(int(((total_dur - total_rem) / total_dur) * 100))

 # --- GANTT CHART KO VERTICAL BANANE KA NAYA LOGIC ---
    def add_gantt_block(self, tid, ttype, duration):
        # Check karein ke kya is Task ID ke liye row pehle se bani hui hai?
        # Agar nahi, to aik naya horizontal layout banayein us task ki row ke liye
        if not hasattr(self, 'gantt_rows'):
            self.gantt_rows = {}
            # Purane horizontal layout ko vertical se badal dein initUI mein
            # Ya yahan clear karke naya set karein
            for i in reversed(range(self.g_inner_layout.count())): 
                self.g_inner_layout.itemAt(i).widget().setParent(None)

        if tid not in self.gantt_rows:
            row_frame = QFrame()
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 5, 0, 5)
            row_layout.setAlignment(Qt.AlignLeft)
            
            # Row ke shuru mein Task ka naam (e.g., Task 5)
            name_label = QLabel(f"T{tid} ")
            name_label.setFixedWidth(50)
            name_label.setStyleSheet("color: #94a3b8; font-weight: bold; border: none;")
            row_layout.addWidget(name_label)
            
            # Is row ko main vertical container mein add karein
            self.g_inner_layout.setDirection(QVBoxLayout.TopToBottom) # Vertical alignment
            self.g_inner_layout.addWidget(row_frame)
            self.gantt_rows[tid] = row_layout

        # Block banayein
        g_block = QLabel(f"{duration}ms")
        color = "#38bdf8" if ttype == "Task" else "#f87171"
        
        # Width ko duration ke hisaab se set karein (taake timeline feel aaye)
        width = max(50, duration // 10) 
        g_block.setFixedSize(width, 30)
        g_block.setAlignment(Qt.AlignCenter)
        g_block.setStyleSheet(f"""
            background-color: {color}; 
            color: black; 
            border: 1px solid #ffffff44; 
            border-radius: 4px; 
            font-size: 10px; 
            font-weight: bold;
        """)
        
        # Sahi row mein block add karein
        self.gantt_rows[tid].addWidget(g_block)

    # --- OTHER FUNCTIONS (MAINTAINED) ---
    def add_task_logic(self):
        duration = int(self.inputs["Duration"].currentText())
        t_type = self.inputs["Type"].currentText()
        priority = self.inputs["Priority"].currentText()
        task_id = len(self.tasks) + 1
        new_task = {"id": task_id, "duration": duration, "remaining_time": duration, "type": t_type, "priority": priority, "widget": None}
        self.tasks.append(new_task)
        self.update_queue_ui(new_task)

    def load_scenario(self, scenario_name):
        self.reset_simulation()
        data = [{"dur": 1000, "type": "Task", "pri": "Medium"}]
        if scenario_name == "Interrupt Storm": data = [{"dur": 500, "type": "Interrupt", "pri": "High"}] * 3
        elif scenario_name == "Heavy Load": data = [{"dur": 5000, "type": "Task", "pri": "Medium"}] * 2
        for item in data:
            tid = len(self.tasks) + 1
            task = {"id": tid, "duration": item["dur"], "remaining_time": item["dur"], "type": item["type"], "priority": item["pri"], "widget": None}
            self.tasks.append(task)
            self.update_queue_ui(task)

    def export_to_csv(self):
        if not self.tasks: return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, 'wb') as f: # Simple logic for export
                pass 

    def reset_simulation(self):
        self.sim_timer.stop()
        self.is_running = False
        self.is_switching = False
        self.last_task_id = None
        self.tasks = []
        self.current_task_index = 0
        self.start_btn.setText("▶ Start")
        self.cpu_circle.setText("IDLE")
        self.cpu_circle.setStyleSheet("border: 6px solid #22c55e; border-radius: 65px; min-width: 130px; min-height: 130px; color: #22c55e; font-weight: bold;")
        self.progress.setValue(0)
        for layout in self.queue_layouts.values():
            while layout.count():
                w = layout.takeAt(0).widget()
                if w: w.deleteLater()
        while self.g_inner_layout.count():
            w = self.g_inner_layout.takeAt(0).widget()
            if w: w.deleteLater()

    def set_algorithm(self, algo_name):
        self.current_algo = algo_name
        self.algo_label.setText(f"Current Algo: {self.current_algo}")
        self.log_display.append(f"<b>[SYS]:</b> Algorithm changed to {algo_name}")

    def sort_tasks_by_algo(self):
        if self.current_algo == "Priority Queue":
            p_map = {"High": 0, "Medium": 1, "Low": 2}
            self.tasks.sort(key=lambda x: (0 if x["type"]=="Interrupt" else 1, p_map.get(x["priority"], 3)))
        elif self.current_algo == "FCFS":
            self.tasks.sort(key=lambda x: x["id"])

    def update_queue_ui(self, task):
        queue_name = "Ready Queue" if task["type"] == "Task" else "Interrupt Queue"
        task_box = QLabel(f"T{task['id']}")
        color = "#38bdf8" if task["type"] == "Task" else "#f87171"
        task_box.setFixedSize(40, 40)
        task_box.setAlignment(Qt.AlignCenter)
        task_box.setStyleSheet(f"background-color: {color}; color: black; font-weight: bold; border-radius: 5px;")
        task["widget"] = task_box
        self.queue_layouts[queue_name].addWidget(task_box)

    def toggle_simulation(self):
        if not self.is_running and self.tasks:
            self.sort_tasks_by_algo()
            self.is_running = True
            self.start_btn.setText("⏸ Pause")
            self.sim_timer.start(self.speed_slider.value())
        else:
            self.is_running = False
            self.start_btn.setText("▶ Start")
            self.sim_timer.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernDashboard()
    window.show()
    sys.exit(app.exec_())
# GAIA Linux Kernel Modifications Specification v1.0

**Status:** Repo-ready architecture specification  
**Scope:** PREEMPT_RT, consciousness-aware scheduling, cgroup v2 reservation, GUARDIAN LSM enforcement  
**Primary objective:** Make NEXUS-grade cross-core coordination predictable enough for sub-10 ms control paths.

---

## 1. Executive Position

GAIA should **not** fork Linux into a permanently exotic kernel first.

The correct production path is:

1. **Mainline-friendly PREEMPT_RT baseline**
2. **CPU isolation + IRQ/threading discipline**
3. **cgroup v2 reservation and protection model**
4. **`sched_ext` consciousness-aware scheduling policy layer**
5. **GUARDIAN implemented as an LSM policy module**
6. **Only then** consider deeper scheduler or MM patches if the measured latency budget still fails

---

## 2. Required kernel config

```text
CONFIG_PREEMPT_RT=y
CONFIG_HIGH_RES_TIMERS=y
CONFIG_IRQ_FORCED_THREADING=y
CONFIG_CGROUPS=y
CONFIG_CGROUP_SCHED=y
CONFIG_UCLAMP_TASK=y
CONFIG_PSI=y
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_SCHED_CLASS_EXT=y
CONFIG_SECURITY=y
CONFIG_BPF_LSM=y
```

---

## 3. GUARDIAN LSM label model

```text
gaia.core=nexus|guardian|terra|aqua|aero|vita|sophia|urbs
gaia.safety=critical|high|normal|background
gaia.data=public|internal|sensitive|consciousness
gaia.actuation=none|recommend|schedule|execute
gaia.risk=green|yellow|red|black
```

---

## 4. Bottom line

GAIA should be built on **PREEMPT_RT Linux with BPF scheduler extensibility, cgroup v2 protection envelopes, and GUARDIAN enforced through LSM hooks**.

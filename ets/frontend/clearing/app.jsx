const { useState: useS, useEffect: useE, useRef: useR } = React;

function makeBlankParticipant(index = 1) {
  return {
    name: `Participant ${index}`,
    sector: "Other",
    initial_emissions: 0,
    free_allocation_ratio: 0,
    penalty_price: 100,
    abatement_type: "linear",
    max_abatement: 0,
    cost_slope: 1,
    threshold_cost: 0,
    mac_blocks: [],
  };
}

function makeBlankYear(label = "2030") {
  return {
    year: String(label),
    total_cap: 0,
    auction_mode: "explicit",
    auction_offered: 0,
    reserved_allowances: 0,
    cancelled_allowances: 0,
    auction_reserve_price: 0,
    minimum_bid_coverage: 0,
    unsold_treatment: "reserve",
    price_lower_bound: 0,
    price_upper_bound: 100,
    banking_allowed: false,
    borrowing_allowed: false,
    borrowing_limit: 0,
    participants: [],
  };
}

function makeBlankScenario(index = 1) {
  return {
    id: `custom_scenario_${Date.now()}_${index}`,
    name: `New Scenario ${index}`,
    color: "#1f6f55",
    description: "Describe the policy design, participants, and transition logic for this scenario.",
    years: [makeBlankYear("2030")],
  };
}

function buildDraftResult(year) {
  const priceFloor = Number(year?.price_lower_bound ?? 0);
  const priceCeiling = Math.max(priceFloor + 1, Number(year?.price_upper_bound ?? 100));
  const participants = year?.participants || [];
  const q = year?.auction_mode === "explicit"
    ? Number(year?.auction_offered ?? year?.auctioned_allowances ?? 0)
    : Math.max(
        0,
        Number(year?.total_cap ?? 0) - participants.reduce(
          (sum, participant) =>
            sum + Number(participant.initial_emissions || 0) * Number(participant.free_allocation_ratio || 0),
          0
        ) - Number(year?.reserved_allowances ?? 0) - Number(year?.cancelled_allowances ?? 0)
      );
  const perParticipant = participants.map((participant) => {
    const initial = Number(participant.initial_emissions || 0);
    const free = initial * Number(participant.free_allocation_ratio || 0);
    const net = Math.max(0, initial - free);
    return {
      name: participant.name,
      initial,
      free,
      abatement: 0,
      residual: initial,
      net_trade: net,
      ratio: participant.free_allocation_ratio || 0,
      allowance_buys: net,
      allowance_sells: Math.max(0, free - initial),
      penalty_emissions: 0,
      abatement_cost: 0,
      allowance_cost: 0,
      penalty_cost: 0,
      sales_revenue: 0,
      total_compliance_cost: 0,
      sector: participant.sector || "Other",
    };
  });
  const baselineTotal = perParticipant.reduce((sum, participant) => sum + participant.net_trade, 0);
  return {
    price: null,
    Q: q,
    totalAbate: 0,
    totalTraded: baselineTotal,
    revenue: 0,
    perParticipant,
    demandCurve: [
      { p: priceFloor, total: baselineTotal, perPart: perParticipant.map((participant) => participant.net_trade) },
      { p: priceCeiling, total: baselineTotal, perPart: perParticipant.map((participant) => participant.net_trade) },
    ],
  };
}

function configsEqual(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function KPI({ label, value, sub, tone }) {
  return (
    <div className={"kpi" + (tone ? " tone-" + tone : "")}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

function buildTechnologyPathway(scenario, results) {
  const years = (scenario?.years || []).map((year) => String(year.year));
  const rows = (scenario?.years?.[0]?.participants || []).map((participant) => {
    const pathway = years.map((year) => {
      const yearResult = results?.[scenario.name]?.[year];
      const match = yearResult?.perParticipant?.find((item) => item.name === participant.name);
      return match?.technology || "Base Technology";
    });
    return { participant: participant.name, pathway };
  });
  return { years, rows };
}

function makeIssue(level, scope, message) {
  return { level, scope, message };
}

function validateMacBlocks(blocks, label) {
  const issues = [];
  if (!Array.isArray(blocks)) {
    issues.push(makeIssue("error", label, "MAC blocks must be provided as a list."));
    return issues;
  }
  let previousCost = -Infinity;
  blocks.forEach((block, index) => {
    const amount = Number(block?.amount ?? 0);
    const cost = Number(block?.marginal_cost ?? 0);
    if (!Number.isFinite(amount) || !Number.isFinite(cost)) {
      issues.push(makeIssue("error", label, `MAC block ${index + 1} must contain numeric amount and marginal cost.`));
      return;
    }
    if (amount < 0 || cost < 0) {
      issues.push(makeIssue("error", label, `MAC block ${index + 1} must be non-negative.`));
    }
    if (cost < previousCost) {
      issues.push(makeIssue("error", label, `MAC blocks must be ordered by non-decreasing marginal cost.`));
    }
    previousCost = cost;
  });
  return issues;
}

function validateTechnology(option, scope) {
  const issues = [];
  if (!option?.name) issues.push(makeIssue("error", scope, "Technology option must have a name."));
  if (Number(option?.initial_emissions ?? 0) < 0) issues.push(makeIssue("error", scope, "Technology emissions must be non-negative."));
  if (Number(option?.free_allocation_ratio ?? 0) < 0 || Number(option?.free_allocation_ratio ?? 0) > 1) {
    issues.push(makeIssue("error", scope, "Technology free allocation ratio must be between 0 and 1."));
  }
  if (Number(option?.penalty_price ?? 0) <= 0) issues.push(makeIssue("error", scope, "Technology penalty price must be positive."));
  if (Number(option?.fixed_cost ?? 0) < 0) issues.push(makeIssue("error", scope, "Technology fixed cost must be non-negative."));
  if (option?.abatement_type === "piecewise" && !(option?.mac_blocks || []).length) {
    issues.push(makeIssue("error", scope, "Piecewise technology option requires MAC blocks."));
  }
  issues.push(...validateMacBlocks(option?.mac_blocks || [], scope));
  return issues;
}

function validateParticipant(participant, yearLabel) {
  const scope = `${yearLabel} · ${participant?.name || "Unnamed participant"}`;
  const issues = [];
  if (!participant?.name) issues.push(makeIssue("error", scope, "Participant must have a name."));
  const emissions = Number(participant?.initial_emissions ?? 0);
  const freeRatio = Number(participant?.free_allocation_ratio ?? 0);
  const penalty = Number(participant?.penalty_price ?? 0);
  if (emissions < 0) issues.push(makeIssue("error", scope, "Initial emissions must be non-negative."));
  if (freeRatio < 0 || freeRatio > 1) issues.push(makeIssue("error", scope, "Free allocation ratio must be between 0 and 1."));
  if (penalty <= 0) issues.push(makeIssue("error", scope, "Penalty price must be positive."));
  if (participant?.abatement_type === "piecewise" && !(participant?.mac_blocks || []).length) {
    issues.push(makeIssue("error", scope, "Piecewise abatement requires MAC blocks."));
  }
  if ((participant?.technology_options || []).length > 0) {
    const techNames = new Set();
    participant.technology_options.forEach((option) => {
      if (techNames.has(option.name)) {
        issues.push(makeIssue("warning", scope, `Duplicate technology option name '${option.name}'.`));
      }
      techNames.add(option.name);
      issues.push(...validateTechnology(option, `${scope} · ${option.name || "Unnamed technology"}`));
    });
  }
  issues.push(...validateMacBlocks(participant?.mac_blocks || [], scope));
  return issues;
}

function validateScenario(scenario) {
  const issues = [];
  if (!scenario) return issues;
  if (!scenario.name) issues.push(makeIssue("error", "Scenario", "Scenario must have a name."));
  if (!(scenario.years || []).length) issues.push(makeIssue("error", "Scenario", "Scenario must contain at least one year."));
  const seenYears = new Set();
  (scenario.years || []).forEach((year) => {
    const yearLabel = String(year?.year || "Unnamed year");
    if (seenYears.has(yearLabel)) issues.push(makeIssue("error", `Year ${yearLabel}`, "Duplicate year label."));
    seenYears.add(yearLabel);
    const participants = year?.participants || [];
    if (!participants.length) issues.push(makeIssue("warning", `Year ${yearLabel}`, "This year has no participants."));
    const lower = Number(year?.price_lower_bound ?? 0);
    const upper = Number(year?.price_upper_bound ?? 0);
    if (upper <= lower) issues.push(makeIssue("error", `Year ${yearLabel}`, "Price ceiling must be greater than price floor."));
    if (year?.borrowing_allowed && Number(year?.borrowing_limit ?? 0) <= 0) {
      issues.push(makeIssue("warning", `Year ${yearLabel}`, "Borrowing is enabled but borrowing limit is zero."));
    }
    if (Number(year?.auction_reserve_price ?? 0) < 0) {
      issues.push(makeIssue("error", `Year ${yearLabel}`, "Auction reserve price must be non-negative."));
    }
    if (Number(year?.minimum_bid_coverage ?? 0) < 0 || Number(year?.minimum_bid_coverage ?? 0) > 1) {
      issues.push(makeIssue("error", `Year ${yearLabel}`, "Minimum bid coverage must be between 0 and 1."));
    }
    if (!["reserve", "cancel", "carry_forward"].includes(String(year?.unsold_treatment ?? "reserve"))) {
      issues.push(makeIssue("error", `Year ${yearLabel}`, "Unsold treatment must be reserve, cancel, or carry_forward."));
    }
    const freeAllocation = participants.reduce(
      (sum, participant) => sum + Number(participant?.initial_emissions ?? 0) * Number(participant?.free_allocation_ratio ?? 0),
      0
    );
    const auctioned = Number(year?.auction_offered ?? year?.auctioned_allowances ?? 0);
    const reserved = Number(year?.reserved_allowances ?? 0);
    const cancelled = Number(year?.cancelled_allowances ?? 0);
    const totalCap = Number(year?.total_cap ?? 0);
    if (year?.auction_mode === "explicit") {
      const allowanceSupply = freeAllocation + auctioned + reserved + cancelled;
      if (allowanceSupply - totalCap > 1e-6) {
        issues.push(makeIssue("error", `Year ${yearLabel}`, `Free allocation + auction offered + reserved + cancelled allowances (${allowanceSupply.toFixed(2)}) exceeds total cap (${totalCap.toFixed(2)}).`));
      } else if (totalCap - allowanceSupply > 1e-6) {
        issues.push(makeIssue("warning", `Year ${yearLabel}`, `Configured supply buckets leave ${(totalCap - allowanceSupply).toFixed(2)} allowances unallocated within the cap.`));
      }
    }
    if (reserved > 0) {
      issues.push(makeIssue("note", `Year ${yearLabel}`, `Reserved allowances remove ${reserved.toFixed(2)} allowances from current-year circulation.`));
    }
    if (cancelled > 0) {
      issues.push(makeIssue("note", `Year ${yearLabel}`, `Cancelled allowances permanently retire ${cancelled.toFixed(2)} allowances from the cap.`));
    }
    if ((year?.auction_reserve_price ?? 0) > 0) {
      issues.push(makeIssue("note", `Year ${yearLabel}`, `Auction reserve price is set at ${Number(year.auction_reserve_price).toFixed(2)}.`));
    }
    if ((year?.minimum_bid_coverage ?? 0) > 0) {
      issues.push(makeIssue("note", `Year ${yearLabel}`, `Minimum bid coverage is set at ${(Number(year.minimum_bid_coverage) * 100).toFixed(0)}% of auction volume.`));
    }
    const names = new Set();
    participants.forEach((participant) => {
      if (names.has(participant.name)) {
        issues.push(makeIssue("error", `Year ${yearLabel}`, `Duplicate participant name '${participant.name}'.`));
      }
      names.add(participant.name);
      issues.push(...validateParticipant(participant, `Year ${yearLabel}`));
    });
  });
  if (!issues.length) {
    issues.push(makeIssue("note", "Scenario", "No validation issues detected for the active scenario."));
  }
  return issues;
}

function ValidationPanel({ issues, title = "Validation" }) {
  const counts = {
    error: issues.filter((issue) => issue.level === "error").length,
    warning: issues.filter((issue) => issue.level === "warning").length,
    note: issues.filter((issue) => issue.level === "note").length,
  };
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">Validation</div>
          <h2>{title}</h2>
          <p className="muted">Pre-run checks on the active scenario configuration.</p>
        </div>
        <div className="validation-summary">
          <span className="validation-pill error">{counts.error} errors</span>
          <span className="validation-pill warning">{counts.warning} warnings</span>
          <span className="validation-pill note">{counts.note} notes</span>
        </div>
      </div>
      <div className="validation-list">
        {issues.map((issue, index) => (
          <div key={`${issue.scope}-${issue.message}-${index}`} className={`validation-item ${issue.level}`}>
            <div className="validation-item-head">
              <span className={`validation-dot ${issue.level}`}></span>
              <strong>{issue.scope}</strong>
            </div>
            <div className="validation-message">{issue.message}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function App() {
  const [templates, setTemplates] = useS([]);
  const [config, setConfig] = useS({ scenarios: [] });
  const [results, setResults] = useS({});
  const [summary, setSummary] = useS([]);
  const [analysis, setAnalysis] = useS([]);
  const [plots, setPlots] = useS([]);
  const [annualPlots, setAnnualPlots] = useS([]);
  const [activeScenarioId, setActiveScenarioId] = useS(null);
  const [activeYear, setActiveYear] = useS(null);
  const [stacked, setStacked] = useS(true);
  const [activeSection, setActiveSection] = useS("build");
  const [selPart, setSelPart] = useS(null);
  const [status, setStatus] = useS("Loading templates…");
  const [tweaksOpen, setTweaksOpen] = useS(false);
  const [tweakState, setTweakState] = useS({
    dark: false,
    chartStyle: "institutional",
    density: "comfortable",
  });
  const configRef = useR(config);
  const loadedConfigRef = useR(null);

  useE(() => {
    configRef.current = config;
  }, [config]);

  useE(() => {
    const onMsg = (e) => {
      if (!e.data || typeof e.data !== "object") return;
      if (e.data.type === "__activate_edit_mode") setTweaksOpen(true);
      if (e.data.type === "__deactivate_edit_mode") setTweaksOpen(false);
    };
    window.addEventListener("message", onMsg);
    window.parent?.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  useE(() => {
    document.documentElement.dataset.theme = tweakState.dark ? "dark" : "light";
    document.documentElement.dataset.chart = tweakState.chartStyle;
    document.documentElement.dataset.density = tweakState.density;
  }, [tweakState]);

  useE(() => {
    loadTemplates();
  }, []);

  async function loadTemplates() {
    try {
      const response = await fetch("/api/templates");
      const payload = await response.json();
      setTemplates(payload.templates || []);
      const defaultTemplate =
        payload.templates?.find((item) => item.id === "example")?.config
        || payload.templates?.find((item) => item.config?.scenarios?.some((scenario) =>
          scenario.years?.some((year) => (year.participants || []).length > 0)
        ))?.config
        || payload.templates?.[0]?.config
        || { scenarios: [] };
      const initialConfig = structuredClone(defaultTemplate);
      setConfig(initialConfig);
      configRef.current = initialConfig;
      loadedConfigRef.current = structuredClone(defaultTemplate);
      const firstScenario = defaultTemplate.scenarios?.[0];
      setActiveScenarioId(firstScenario?.id || null);
      setActiveYear(firstScenario?.years?.[0]?.year || null);
      setResults({});
      setSummary([]);
      setAnalysis([]);
      setPlots([]);
      setAnnualPlots([]);
      setStatus("Template loaded. Review or edit inputs, then run the scenario.");
    } catch (error) {
      setStatus(`Failed to load templates: ${error.message}`);
    }
  }

  async function runSimulation(configOverride = null) {
    const payloadConfig = structuredClone(configOverride || configRef.current);
    setStatus("Running model…");
    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadConfig),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Run failed.");
      }
      setConfig(payload.config);
      setResults(payload.results || {});
      setSummary(payload.summary || []);
      setAnalysis(payload.analysis || []);
      setPlots(payload.plots || []);
      setAnnualPlots(payload.annual_plots || []);
      if (!activeScenarioId && payload.config?.scenarios?.length) {
        setActiveScenarioId(payload.config.scenarios[0].id);
      }
      const scenario = payload.config?.scenarios?.find((s) => s.id === activeScenarioId)
        || payload.config?.scenarios?.[0];
      if (scenario && !scenario.years.some((y) => String(y.year) === String(activeYear))) {
        setActiveYear(scenario.years?.[0]?.year || null);
      }
      setStatus(`Simulation complete. Results written to ${payload.output_dir}`);
    } catch (error) {
      setStatus(`Run failed: ${error.message}`);
    }
  }

  const scenarios = config.scenarios || [];
  const activeScenario = scenarios.find((s) => s.id === activeScenarioId) || scenarios[0];
  const yearObj = activeScenario?.years?.find((y) => String(y.year) === String(activeYear)) || activeScenario?.years?.[0];
  const result = activeScenario && yearObj ? results?.[activeScenario.name]?.[String(yearObj.year)] : null;
  const displayResult = yearObj ? (result || buildDraftResult(yearObj)) : null;
  const hasEditedChanges = loadedConfigRef.current ? !configsEqual(config, loadedConfigRef.current) : false;
  const validationIssues = validateScenario(activeScenario);

  const commitConfig = (updater) => {
    setConfig((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      configRef.current = next;
      return next;
    });
  };

  const updateYear = (newYear) => {
    commitConfig((prev) => ({
      ...prev,
      scenarios: prev.scenarios.map((scenario) =>
        scenario.id !== activeScenario.id
          ? scenario
          : {
              ...scenario,
              years: scenario.years.map((year) =>
                String(year.year) === String(yearObj.year) ? { ...year, ...newYear } : year
              ),
            }
      ),
    }));
  };

  const updateScenario = (patch) => {
    commitConfig((prev) => ({
      ...prev,
      scenarios: prev.scenarios.map((scenario) =>
        scenario.id === activeScenario.id ? { ...scenario, ...patch } : scenario
      ),
    }));
  };

  const addScenario = () => {
    const nextIndex = (scenarios || []).length + 1;
    const nextScenario = makeBlankScenario(nextIndex);
    commitConfig((prev) => ({
      ...prev,
      scenarios: [...prev.scenarios, nextScenario],
    }));
    setActiveScenarioId(nextScenario.id);
    setActiveYear(String(nextScenario.years[0]?.year || "2030"));
    setSelPart(null);
    setStatus(`Added ${nextScenario.name}. Configure it step by step, then run the scenario.`);
  };

  const duplicateScenario = () => {
    if (!activeScenario) return;
    const nextScenario = structuredClone(activeScenario);
    nextScenario.id = `custom_scenario_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    nextScenario.name = `${activeScenario.name} Copy`;
    commitConfig((prev) => ({
      ...prev,
      scenarios: [...prev.scenarios, nextScenario],
    }));
    setActiveScenarioId(nextScenario.id);
    setActiveYear(String(nextScenario.years?.[0]?.year || "2030"));
    setSelPart(null);
    setStatus(`Duplicated ${activeScenario.name}.`);
  };

  const removeScenario = () => {
    if (!activeScenario || scenarios.length <= 1) return;
    const remaining = scenarios.filter((scenario) => scenario.id !== activeScenario.id);
    commitConfig((prev) => ({
      ...prev,
      scenarios: remaining,
    }));
    setActiveScenarioId(remaining[0]?.id || null);
    setActiveYear(String(remaining[0]?.years?.[0]?.year || ""));
    setSelPart(null);
    setStatus(`Removed ${activeScenario.name}.`);
  };

  const addYear = () => {
    if (!activeScenario) return;
    const existingYears = activeScenario.years.map((item) => Number(item.year)).filter(Number.isFinite);
    const nextYear = existingYears.length ? Math.max(...existingYears) + 5 : 2030;
    const templateParticipants = yearObj?.participants?.length
      ? yearObj.participants.map((participant) => ({ ...participant }))
      : [makeBlankParticipant(1)];
    const nextYearConfig = {
      ...makeBlankYear(nextYear),
      participants: templateParticipants,
    };

    commitConfig((prev) => ({
      ...prev,
      scenarios: prev.scenarios.map((scenario) =>
        scenario.id !== activeScenario.id
          ? scenario
          : { ...scenario, years: [...scenario.years, nextYearConfig] }
      ),
    }));
    setActiveYear(String(nextYear));
  };

  const saveScenarioYear = (scenarioDraft, yearDraft, originalYear) => {
    if (!activeScenario) return;
    commitConfig((prev) => ({
      ...prev,
      scenarios: prev.scenarios.map((scenario) =>
        scenario.id !== activeScenario.id
          ? scenario
          : {
              ...scenario,
              ...scenarioDraft,
              years: scenario.years.map((item) =>
                String(item.year) === String(originalYear) ? { ...yearDraft } : item
              ),
            }
      ),
    }));
    setActiveYear(String(yearDraft.year));
    setStatus(`Saved changes for ${scenarioDraft.name} · ${yearDraft.year}`);
  };

  const updateYearSeriesValue = (field, valuesByYear) => {
    if (!activeScenario) return;
    commitConfig((prev) => ({
      ...prev,
      scenarios: prev.scenarios.map((scenario) =>
        scenario.id !== activeScenario.id
          ? scenario
          : {
              ...scenario,
              years: scenario.years.map((item) => ({
                ...item,
                [field]: valuesByYear[String(item.year)] ?? item[field],
              })),
            }
      ),
    }));
    setStatus(`Updated ${field.replaceAll("_", " ")} across ${activeScenario.name}.`);
  };

  const removeYear = () => {
    if (!activeScenario || activeScenario.years.length <= 1) return;
    const nextYears = activeScenario.years.filter((item) => String(item.year) !== String(yearObj.year));
    commitConfig((prev) => ({
      ...prev,
      scenarios: prev.scenarios.map((scenario) =>
        scenario.id !== activeScenario.id ? scenario : { ...scenario, years: nextYears }
      ),
    }));
    setActiveYear(String(nextYears[0]?.year || ""));
    setSelPart(null);
  };

  const dragSupply = (newQ) => {
    const clamped = Math.max(0, newQ);
    if (yearObj.auction_mode === "explicit") {
      updateYear({ ...yearObj, auction_offered: clamped });
    } else {
      const free = yearObj.participants.reduce(
        (sum, participant) => sum + (participant.initial_emissions || 0) * (participant.free_allocation_ratio || 0),
        0
      );
      updateYear({ ...yearObj, total_cap: clamped + free });
    }
  };

  if (!activeScenario || !yearObj || !displayResult) {
    return <div className="wb"><p>{status}</p></div>;
  }

  return (
    <div className="app">
      <Header
        scenarios={scenarios}
        templates={templates}
        activeId={activeScenario.id}
        onSelectScenario={setActiveScenarioId}
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        onAddScenario={addScenario}
        onDuplicateScenario={duplicateScenario}
        onRemoveScenario={removeScenario}
        onLoadTemplate={(templateId) => {
          const template = templates.find((item) => item.id === templateId);
          if (!template) return;
          const nextConfig = structuredClone(template.config);
          setConfig(nextConfig);
          configRef.current = nextConfig;
          loadedConfigRef.current = structuredClone(template.config);
          setResults({});
          setSummary([]);
          setAnalysis([]);
          setPlots([]);
          setAnnualPlots([]);
          setActiveScenarioId(nextConfig.scenarios?.[0]?.id || null);
          setActiveYear(nextConfig.scenarios?.[0]?.years?.[0]?.year || null);
          setSelPart(null);
          setStatus(`Loaded template: ${template.name}. Click Run scenario to solve the market.`);
        }}
        onRun={() => {
          const baseConfig = structuredClone(loadedConfigRef.current || configRef.current);
          setConfig(baseConfig);
          configRef.current = baseConfig;
          runSimulation(baseConfig);
        }}
        onRunEdited={() => runSimulation()}
        hasEditedChanges={hasEditedChanges}
        status={status}
      />

      {activeSection === "build" && (
        <BuildView
          scenario={activeScenario}
          yearObj={yearObj}
          onYearChange={(year) => { setActiveYear(year); setSelPart(null); }}
          activeYear={activeYear}
          updateYear={updateYear}
          updateScenario={updateScenario}
          addYear={addYear}
          removeYear={removeYear}
          onSave={saveScenarioYear}
          onUpdateYearSeries={updateYearSeriesValue}
          validationIssues={validationIssues}
          onRunBase={() => {
            const baseConfig = structuredClone(loadedConfigRef.current || configRef.current);
            setConfig(baseConfig);
            configRef.current = baseConfig;
            runSimulation(baseConfig);
          }}
          onRunEdited={() => runSimulation()}
          hasEditedChanges={hasEditedChanges}
        />
      )}

      {activeSection === "model" && (
        <ModelView
          scenario={activeScenario}
          yearObj={yearObj}
          activeYear={activeYear}
          onYearChange={(year) => { setActiveYear(year); setSelPart(null); }}
          selPart={selPart}
          setSelPart={setSelPart}
          onRunBase={() => {
            const baseConfig = structuredClone(loadedConfigRef.current || configRef.current);
            setConfig(baseConfig);
            configRef.current = baseConfig;
            runSimulation(baseConfig);
          }}
          onRunEdited={() => runSimulation()}
          hasEditedChanges={hasEditedChanges}
          validationIssues={validationIssues}
        />
      )}

      {activeSection === "analysis" && (
        <AnalysisView
          scenario={activeScenario}
          yearObj={yearObj}
          onYearChange={(year) => { setActiveYear(year); setSelPart(null); }}
          activeYear={activeYear}
          result={displayResult}
          results={results}
          scenarios={scenarios}
          stacked={stacked}
          onToggleStacked={() => setStacked((value) => !value)}
          dragSupply={dragSupply}
          selPart={selPart}
          setSelPart={setSelPart}
          analysis={analysis}
          annualPlots={annualPlots}
          marketPlots={plots}
        />
      )}

      {activeSection === "scenario" && (
        <Compare scenarios={scenarios} results={results} activeYear={activeYear} onYear={setActiveYear} />
      )}

      <Tweaks open={tweaksOpen} state={tweakState} setState={setTweakState} />
    </div>
  );
}

function Header({
  scenarios,
  templates,
  activeId,
  onSelectScenario,
  activeSection,
  onSelectSection,
  onLoadTemplate,
  onAddScenario,
  onDuplicateScenario,
  onRemoveScenario,
  status,
}) {
  const [selectedTemplate, setSelectedTemplate] = useS(templates?.[0]?.id || "blank");
  const sections = [
    { id: "build", label: "Build" },
    { id: "model", label: "Model" },
    { id: "analysis", label: "Analysis" },
    { id: "scenario", label: "Scenario" },
  ];
  useE(() => {
    if (templates.length && !templates.some((item) => item.id === selectedTemplate)) {
      setSelectedTemplate(templates[0].id);
    }
  }, [templates]);

  return (
    <header className="hdr">
      <div className="hdr-top">
        <div className="hdr-brand">
          <div className="mark">
            <svg viewBox="0 0 40 40" width="28" height="28">
              <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M4 26 Q14 22 20 20 T36 14" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <line x1="4" x2="36" y1="20" y2="20" stroke="currentColor" strokeWidth="1" strokeDasharray="2 2"/>
              <circle cx="20" cy="20" r="3" fill="currentColor"/>
            </svg>
          </div>
          <div>
            <div className="brand-title">Clearing</div>
            <div className="brand-sub">{status}</div>
          </div>
        </div>
        <div className="hdr-actions">
          <nav className="hdr-sections">
            {sections.map((section) => (
              <button
                key={section.id}
                className={"section-tab " + (activeSection === section.id ? "on" : "")}
                onClick={() => onSelectSection(section.id)}
              >
                {section.label}
              </button>
            ))}
          </nav>
        </div>
      </div>
      {activeSection === "build" && (
        <div className="hdr-tools">
          <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value)}>
            {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
          </select>
          <button className="ghost-btn" onClick={() => onLoadTemplate(selectedTemplate)}>Load template</button>
          <button className="ghost-btn" onClick={onAddScenario}>Add scenario</button>
          <button className="ghost-btn" onClick={onDuplicateScenario}>Duplicate scenario</button>
          <button className="ghost-btn danger-btn" onClick={onRemoveScenario} disabled={scenarios.length <= 1}>Remove scenario</button>
        </div>
      )}
      <nav className="hdr-scenarios">
        {scenarios.map((scenario) => (
          <button
            key={scenario.id}
            className={"pill-btn " + (activeId === scenario.id ? "on" : "")}
            onClick={() => onSelectScenario(scenario.id)}
            style={{ "--c": scenario.color }}
          >
            <i className="sw" style={{ background: scenario.color }}></i>{scenario.name}
          </button>
        ))}
      </nav>
    </header>
  );
}

function ScenarioHero({ scenario, activeYear, onYearChange, results, primaryMetric = null, secondaryMetric = null }) {
  const resByYear = results?.[scenario.name] || {};
  return (
    <section className="wb-hero">
      <div className="scenario-meta">
        <div className="eyebrow">Scenario</div>
        <h1 style={{ color: scenario.color }}>{scenario.name}</h1>
        <p className="lede">{scenario.description}</p>
        <div className="year-strip">
          {scenario.years.map((year) => (
            <button
              key={year.year}
              className={"ystep " + (String(year.year) === String(activeYear) ? "on" : "")}
              onClick={() => onYearChange(String(year.year))}
            >
              <div className="yv">{year.year}</div>
              <div className="yp">{fmt.price(resByYear[String(year.year)]?.price)}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="hero-side">
        {primaryMetric}
        {secondaryMetric}
      </div>
    </section>
  );
}

function YearSeriesModal({ title, field, years, onClose, onSave }) {
  const [draft, setDraft] = useS(() =>
    Object.fromEntries((years || []).map((year) => [String(year.year), year[field] ?? 0]))
  );

  useE(() => {
    setDraft(Object.fromEntries((years || []).map((year) => [String(year.year), year[field] ?? 0])));
  }, [field, years]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="panel-head">
          <div>
            <div className="eyebrow">Year series editor</div>
            <h2>{title}</h2>
            <p className="muted">Set the value for each year in the selected scenario, then save the full series.</p>
          </div>
          <button className="ghost-btn" onClick={onClose}>Close</button>
        </div>
        <div className="pathway-table-wrap">
          <table className="pathway-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {(years || []).map((year) => (
                <tr key={year.year}>
                  <td>{year.year}</td>
                  <td>
                    <input
                      className="text"
                      type="number"
                      value={draft[String(year.year)]}
                      onChange={(event) => setDraft((current) => ({
                        ...current,
                        [String(year.year)]: Number(event.target.value),
                      }))}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="hero-actions">
          <button className="ghost-btn" onClick={onClose}>Cancel</button>
          <button
            className="ghost-btn on"
            onClick={() => {
              onSave(field, draft);
              onClose();
            }}
          >
            Save series
          </button>
        </div>
      </div>
    </div>
  );
}

function BuildView({
  scenario, yearObj, activeYear, onYearChange, updateYear, updateScenario, addYear, removeYear,
  onRunBase, onRunEdited, hasEditedChanges, onSave, onUpdateYearSeries, validationIssues,
}) {
  const [seriesField, setSeriesField] = useS(null);
  const seriesFields = [
    { key: "total_cap", label: "Total cap" },
    { key: "auction_offered", label: "Auction offered" },
    { key: "reserved_allowances", label: "Reserved allowances" },
    { key: "cancelled_allowances", label: "Cancelled allowances" },
    { key: "auction_reserve_price", label: "Auction reserve price" },
    { key: "minimum_bid_coverage", label: "Minimum bid coverage" },
    { key: "price_lower_bound", label: "Price floor" },
    { key: "price_upper_bound", label: "Price ceiling" },
    { key: "borrowing_limit", label: "Borrowing limit" },
  ];
  return (
    <div className="wb">
      <ScenarioHero
        scenario={scenario}
        activeYear={activeYear}
        onYearChange={onYearChange}
        results={{}}
        primaryMetric={(
          <div className="panel hero-panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">Build</div>
                <h2>Scenario builder</h2>
                <p className="muted">Create or import a scenario, edit assumptions, then run directly from here.</p>
              </div>
            </div>
            <div className="hero-actions">
              <button className="ghost-btn" onClick={onRunBase}>Run loaded scenario</button>
              <button className={"ghost-btn on " + (hasEditedChanges ? "edited-btn" : "")} onClick={onRunEdited}>Run edited</button>
            </div>
          </div>
        )}
      />
      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Market timeline</div>
            <h2>Review values across years</h2>
            <p className="muted">Click a market attribute to open a year-by-year editor for the whole scenario period.</p>
          </div>
        </div>
        <div className="review-grid">
          {seriesFields.map((field) => (
            <button key={field.key} className="review-item review-button" onClick={() => setSeriesField(field.key)}>
              <span className="review-label">{field.label}</span>
              <strong>{fmt.num(yearObj[field.key] || 0, 0)}</strong>
              <span className="muted">{scenario.years.map((year) => `${year.year}: ${fmt.num(year[field.key] || 0, 0)}`).join(" · ")}</span>
            </button>
          ))}
        </div>
      </section>
      <ValidationPanel issues={validationIssues} title="Build validation" />
      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Build</div>
            <h2>Edit scenario inputs</h2>
            <p className="muted">Build from scratch, use templates, and edit year, participant, MAC, and technology assumptions.</p>
          </div>
        </div>
        <Editor
          scenario={scenario}
          year={yearObj}
          onSave={onSave}
          onAddYear={addYear}
          onRemoveYear={removeYear}
          onSelectYear={onYearChange}
        />
      </section>
      {seriesField && (
        <YearSeriesModal
          title={seriesFields.find((field) => field.key === seriesField)?.label || seriesField}
          field={seriesField}
          years={scenario.years}
          onClose={() => setSeriesField(null)}
          onSave={onUpdateYearSeries}
        />
      )}
    </div>
  );
}

function ModelView({
  scenario, yearObj, activeYear, onYearChange, selPart, setSelPart, onRunBase, onRunEdited, hasEditedChanges, validationIssues,
}) {
  const selectedIndex = selPart == null ? 0 : selPart;
  const selectedParticipant = yearObj.participants?.[selectedIndex] || null;
  const freeAllocation = (yearObj.participants || []).reduce(
    (sum, participant) => sum + Number(participant.initial_emissions || 0) * Number(participant.free_allocation_ratio || 0),
    0
  );
  const unallocatedAllowances = Math.max(
    0,
    Number(yearObj.total_cap || 0)
      - freeAllocation
      - Number(yearObj.auction_offered || 0)
      - Number(yearObj.reserved_allowances || 0)
      - Number(yearObj.cancelled_allowances || 0)
  );
  return (
    <div className="wb">
      <ScenarioHero
        scenario={scenario}
        activeYear={activeYear}
        onYearChange={onYearChange}
        results={{}}
        primaryMetric={(
          <div className="panel hero-panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">Model</div>
                <h2>Review built model</h2>
                <p className="muted">Inspect the scenario structure before running: market rules, participants, MACs, and technology pathways.</p>
              </div>
            </div>
            <div className="hero-actions">
              <button className="ghost-btn" onClick={onRunBase}>Run loaded scenario</button>
              <button className={"ghost-btn on " + (hasEditedChanges ? "edited-btn" : "")} onClick={onRunEdited}>Run edited</button>
            </div>
          </div>
        )}
      />
      <section className="wb-grid">
        <ValidationPanel issues={validationIssues} title="Model validation" />
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Market</div>
              <h2>Year {yearObj.year} market definition</h2>
            </div>
          </div>
          <div className="review-grid">
            <div className="review-item"><span className="review-label">Auction mode</span><strong>{yearObj.auction_mode}</strong></div>
            <div className="review-item"><span className="review-label">Total cap</span><strong>{fmt.num(yearObj.total_cap || 0, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Auction offered</span><strong>{fmt.num(yearObj.auction_offered || 0, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Reserved allowances</span><strong>{fmt.num(yearObj.reserved_allowances || 0, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Cancelled allowances</span><strong>{fmt.num(yearObj.cancelled_allowances || 0, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Unallocated allowances</span><strong>{fmt.num(unallocatedAllowances, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Auction reserve price</span><strong>{fmt.num(yearObj.auction_reserve_price || 0, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Minimum bid coverage</span><strong>{fmt.num(yearObj.minimum_bid_coverage || 0, 2)}</strong></div>
            <div className="review-item"><span className="review-label">Unsold treatment</span><strong>{yearObj.unsold_treatment || "reserve"}</strong></div>
            <div className="review-item"><span className="review-label">Price bounds</span><strong>{fmt.num(yearObj.price_lower_bound || 0, 0)} to {fmt.num(yearObj.price_upper_bound || 0, 0)}</strong></div>
            <div className="review-item"><span className="review-label">Banking</span><strong>{yearObj.banking_allowed ? "enabled" : "disabled"}</strong></div>
            <div className="review-item"><span className="review-label">Borrowing</span><strong>{yearObj.borrowing_allowed ? `enabled (${fmt.num(yearObj.borrowing_limit || 0, 0)})` : "disabled"}</strong></div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Participants</div>
              <h2>Configured participants</h2>
            </div>
          </div>
          <div className="pathway-table-wrap">
            <table className="pathway-table">
              <thead>
                <tr>
                  <th>Participant</th>
                  <th>Sector</th>
                  <th>Emissions</th>
                  <th>Abatement</th>
                  <th>Technology options</th>
                </tr>
              </thead>
              <tbody>
                {(yearObj.participants || []).map((participant, index) => (
                  <tr key={`${participant.name}-${index}`} onClick={() => setSelPart(index)}>
                    <td>{participant.name}</td>
                    <td>{participant.sector || "Other"}</td>
                    <td>{fmt.num(participant.initial_emissions || 0, 0)}</td>
                    <td>{participant.abatement_type}</td>
                    <td>{(participant.technology_options || []).length || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
      <section className="wb-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">MAC</div>
              <h2>Selected participant MAC</h2>
            </div>
            <div className="panel-controls">
              <select
                value={selectedIndex}
                onChange={(event) => setSelPart(Number(event.target.value))}
              >
                {(yearObj.participants || []).map((participant, index) => (
                  <option key={`${participant.name}-${index}`} value={index}>{participant.name}</option>
                ))}
              </select>
            </div>
          </div>
          <ParticipantMacChart participant={selectedParticipant} outcome={null} carbonPrice={null} />
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Technology</div>
              <h2>Technology pathway setup</h2>
            </div>
          </div>
          <div className="pathway-table-wrap">
            <table className="pathway-table">
              <thead>
                <tr>
                  <th>Technology</th>
                  <th>Emissions</th>
                  <th>Free ratio</th>
                  <th>Fixed cost</th>
                </tr>
              </thead>
              <tbody>
                {((selectedParticipant?.technology_options || []).length ? selectedParticipant.technology_options : [{
                  name: "Base Technology",
                  initial_emissions: selectedParticipant?.initial_emissions || 0,
                  free_allocation_ratio: selectedParticipant?.free_allocation_ratio || 0,
                  fixed_cost: 0,
                }]).map((option, index) => (
                  <tr key={`${option.name}-${index}`}>
                    <td>{option.name}</td>
                    <td>{fmt.num(option.initial_emissions || 0, 1)}</td>
                    <td>{fmt.num(option.free_allocation_ratio || 0, 2)}</td>
                    <td>{fmt.num(option.fixed_cost || 0, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

function AnalysisView({
  scenario, yearObj, activeYear, onYearChange, result, results, scenarios, stacked,
  onToggleStacked, dragSupply, selPart, setSelPart,
  analysis, annualPlots, marketPlots,
}) {
  const yearKeys = scenario.years.map((year) => String(year.year));
  const resByYear = results[scenario.name] || {};
  const idx = yearKeys.indexOf(String(activeYear));
  const prevYear = idx > 0 ? yearKeys[idx - 1] : null;
  const prevResult = prevYear ? resByYear[prevYear] : null;
  const delta = (current, previous) => previous == null ? null : current - previous;
  const filteredAnnualPlots = annualPlots.filter((plot) => plot.includes(slugify(scenario.name)));
  const filteredMarketPlots = marketPlots.filter((plot) => plot.includes(slugify(scenario.name)));
  const selectedIndex = selPart == null ? 0 : selPart;
  const selectedParticipant = yearObj.participants?.[selectedIndex] || null;
  const selectedOutcome = result.perParticipant?.[selectedIndex] || null;
  const technologyPathway = buildTechnologyPathway(scenario, results);

  return (
    <div className="wb">
      <ScenarioHero
        scenario={scenario}
        activeYear={activeYear}
        onYearChange={onYearChange}
        results={results}
        primaryMetric={(
          <div className="kpis">
            <KPI
              label="Equilibrium price"
              value={fmt.price(result.price)}
              sub={prevResult ? `${delta(result.price, prevResult.price) >= 0 ? "▲" : "▼"} ${fmt.num(Math.abs(delta(result.price, prevResult.price)), 2)} vs ${prevYear}` : "base year"}
              tone="primary"
            />
            <KPI label="Auction revenue" value={fmt.money(result.revenue)} sub={`${fmt.int(result.Q)} allowances × ${fmt.price(result.price)}`}/>
            <KPI label="Abatement" value={`${fmt.num(result.totalAbate, 0)} Mt`} sub={prevResult ? `${delta(result.totalAbate, prevResult.totalAbate) >= 0 ? "▲" : "▼"} ${fmt.num(Math.abs(delta(result.totalAbate, prevResult.totalAbate)), 1)} Mt` : "—"}/>
            <KPI label="Allowances traded" value={fmt.num(result.totalTraded, 0)} sub="between buyers & sellers"/>
          </div>
        )}
      />

      <section className="wb-grid">
        <div className="panel panel-chart">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Figure 1</div>
              <h2>Market clearing · {yearObj.year}</h2>
              <p className="muted">Where aggregate net participant demand meets auctioned supply. Drag the supply line to edit the year settings, then rerun the model.</p>
            </div>
            <div className="toggles">
              <button className={"toggle " + (stacked ? "on" : "")} onClick={onToggleStacked}>Stack by participant</button>
            </div>
          </div>
          <MarketChart year={yearObj} result={result} stacked={stacked} onDragSupply={dragSupply} sectorColors={SECTOR_COLORS} />
        </div>

        <div className="panel panel-trajectory">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Figure 2</div>
              <h2>Price trajectory across scenarios</h2>
              <p className="muted">How this scenario compares against the others over time.</p>
            </div>
          </div>
          <TrajectoryChart scenarios={scenarios} results={results} highlightScenario={scenario.name} />
        </div>
      </section>

      <section className="panel panel-parts">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Figure 3</div>
            <h2>Participant drilldown · {yearObj.year}</h2>
          </div>
        </div>
        <ParticipantPanel year={yearObj} result={result} selectedIdx={selPart} onSelectParticipant={(index) => setSelPart(index === selPart ? null : index)} sectorColors={SECTOR_COLORS} />
      </section>

      <section className="wb-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Figure 4</div>
              <h2>Selected participant MAC</h2>
              <p className="muted">
                Marginal abatement cost schedule for {selectedParticipant?.name || "the selected participant"} at {yearObj.year}.
              </p>
            </div>
            <div className="panel-controls">
              <select
                value={selectedIndex}
                onChange={(event) => setSelPart(Number(event.target.value))}
              >
                {(yearObj.participants || []).map((participant, index) => (
                  <option key={`${participant.name}-${index}`} value={index}>
                    {participant.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <ParticipantMacChart
            participant={selectedParticipant}
            outcome={selectedOutcome}
            carbonPrice={result.price}
          />
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Analysis</div>
              <h2>Model interpretation</h2>
            </div>
          </div>
          <ul className="analysis-list">
            {analysis.filter((item) => item.includes(scenario.name)).map((item, index) => <li key={index}>{item}</li>)}
          </ul>
        </div>
      </section>

      <section className="wb-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Figure 5</div>
              <h2>Annual market pathway</h2>
              <p className="muted">Annual trajectory of equilibrium price, abatement, and auction revenue for this scenario.</p>
            </div>
          </div>
          <div className="chart-gallery">
            {filteredAnnualPlots.map((plot, index) => (
              <figure key={plot} className="chart-card chart-card-annual">
                <div className="chart-card-head">
                  <span className="chart-card-kicker">Pathway Chart {index + 1}</span>
                  <span className="chart-card-tag">Annual</span>
                </div>
                <img key={plot} className="result-img compact" src={plot} alt="Annual market pathway" />
                <figcaption className="chart-card-caption">
                  Shows how the scenario evolves across years rather than only in the selected year.
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
        <div className="panel panel-note">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Calibration</div>
              <h2>About the sample MACs</h2>
            </div>
          </div>
          <p className="muted">
            The participant MACs bundled in the example scenarios are demonstration inputs. They are economically coherent, but they are not calibrated sector estimates.
          </p>
          <p className="muted">
            For policy analysis, treat them as placeholders until you replace them with engineering, benchmarking, or observed-firm data for the selected participant.
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Technology pathway</div>
            <h2>Chosen technologies across years</h2>
            <p className="muted">The annual technology selected by the optimization for each participant in this scenario.</p>
          </div>
        </div>
        <div className="pathway-table-wrap">
          <table className="pathway-table">
            <thead>
              <tr>
                <th>Participant</th>
                {technologyPathway.years.map((year) => <th key={year}>{year}</th>)}
              </tr>
            </thead>
            <tbody>
              {technologyPathway.rows.map((row) => (
                <tr key={row.participant}>
                  <td>{row.participant}</td>
                  {row.pathway.map((technology, index) => (
                    <td key={`${row.participant}-${technologyPathway.years[index]}`}>{technology}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Figure 6</div>
            <h2>Exported market visuals</h2>
            <p className="muted">Saved chart outputs for reporting, sharing, or external review of this scenario.</p>
          </div>
        </div>
        <div className="chart-gallery">
          {filteredMarketPlots.map((plot, index) => (
            <figure key={plot} className="chart-card chart-card-export">
              <div className="chart-card-head">
                <span className="chart-card-kicker">Export {index + 1}</span>
                <span className="chart-card-tag">Saved figure</span>
              </div>
              <img key={plot} className="result-img" src={plot} alt="Exported market visual" />
              <figcaption className="chart-card-caption">
                Export-ready figure generated from the backend run for this scenario-year.
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      <footer className="foot">
        <span>Numerical method · Brent root finding in Python</span>
        <span>·</span>
        <span>Source of truth · backend model in <code>ets/participant.py</code> and <code>ets/market.py</code></span>
        <span>·</span>
        <span>Inputs are editable in the UI; rerun the scenario to refresh results</span>
      </footer>
    </div>
  );
}

function Compare({ scenarios, results, activeYear, onYear }) {
  const allYears = [...new Set(scenarios.flatMap((scenario) => scenario.years.map((year) => String(year.year))))].sort();
  return (
    <div className="cmp">
      <div className="cmp-head">
        <div>
          <div className="eyebrow">Side-by-side</div>
          <h1>Three futures, one market</h1>
          <p className="lede">Equilibrium outcomes for each scenario in {activeYear}. The scarcer the cap, the higher the price.</p>
        </div>
        <div className="year-picker">
          {allYears.map((year) => (
            <button key={year} className={"pill-btn " + (year === activeYear ? "on" : "")} onClick={() => onYear(year)}>{year}</button>
          ))}
        </div>
      </div>
      <div className="cmp-grid">
        {scenarios.map((scenario) => {
          const year = scenario.years.find((item) => String(item.year) === String(activeYear));
          if (!year) return null;
          const result = results[scenario.name]?.[String(year.year)];
          if (!result) return null;
          return (
            <div key={scenario.id} className="cmp-card" style={{ "--c": scenario.color }}>
              <div className="cmp-card-head">
                <i className="sw" style={{ background: scenario.color }}></i>
                <h3>{scenario.name}</h3>
              </div>
              <div className="cmp-big">
                <div className="cmp-price">{fmt.price(result.price)}</div>
                <div className="cmp-sub">per tCO₂ · {activeYear}</div>
              </div>
              <div className="cmp-kpis">
                <div><div className="lbl">Abatement</div><div className="val">{fmt.num(result.totalAbate, 0)} Mt</div></div>
                <div><div className="lbl">Auction revenue</div><div className="val">{fmt.money(result.revenue)}</div></div>
                <div><div className="lbl">Auction sold</div><div className="val">{fmt.int(result.Q)}</div></div>
              </div>
              <MiniMarket year={year} result={result} />
              <div className="cmp-parts">
                {result.perParticipant.map((participant, index) => (
                  <div key={index} className="cmp-prow">
                    <span className="n">{participant.name}</span>
                    <span className={"v " + (participant.net_trade > 0 ? "buy" : participant.net_trade < 0 ? "sell" : "")}>
                      {participant.net_trade > 0 ? "buys " : participant.net_trade < 0 ? "sells " : ""}
                      {fmt.num(Math.abs(participant.net_trade), 1)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <div className="panel cmp-trajectory">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Trajectory</div>
            <h2>Price path to {allYears[allYears.length - 1]}</h2>
          </div>
        </div>
        <TrajectoryChart scenarios={scenarios} results={results} />
      </div>
    </div>
  );
}

function MiniMarket({ year, result }) {
  const W = 280, H = 120;
  const PAD = { t: 10, r: 10, b: 22, l: 30 };
  const iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b;
  const curve = result.demandCurve || [];
  const xMin = year.price_lower_bound ?? 0;
  const xMax = year.price_upper_bound ?? 250;
  const yMax = Math.max(result.Q * 1.4, ...curve.map((point) => point.total), 10);
  const yMin = Math.min(0, ...curve.map((point) => point.total));
  const xs = (p) => PAD.l + ((p - xMin) / (xMax - xMin)) * iw;
  const ys = (a) => PAD.t + ih - ((a - yMin) / (yMax - yMin)) * ih;
  const d = curve.map((point, index) => `${index === 0 ? "M" : "L"}${xs(point.p)},${ys(point.total)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mini-chart">
      <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} className="axis"/>
      <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={H - PAD.b} className="axis"/>
      <line x1={PAD.l} x2={W - PAD.r} y1={ys(result.Q)} y2={ys(result.Q)} className="supply-line"/>
      <path d={d} className="demand-line"/>
      {isFinite(result.price) && (
        <>
          <line x1={xs(result.price)} x2={xs(result.price)} y1={ys(result.Q)} y2={H - PAD.b} className="eq-guide" strokeDasharray="2 2"/>
          <circle cx={xs(result.price)} cy={ys(result.Q)} r="4" className="eq-dot"/>
        </>
      )}
    </svg>
  );
}

function Tweaks({ open, state, setState }) {
  if (!open) return null;
  const set = (patch) => {
    const next = { ...state, ...patch };
    setState(next);
    window.parent?.postMessage({ type: "__edit_mode_set_keys", edits: patch }, "*");
  };
  return (
    <div className="tweaks">
      <div className="tweaks-head">Tweaks</div>
      <label><span>Theme</span>
        <div className="seg">
          <button className={state.dark ? "" : "on"} onClick={() => set({ dark: false })}>Light</button>
          <button className={state.dark ? "on" : ""} onClick={() => set({ dark: true })}>Dark</button>
        </div>
      </label>
      <label><span>Chart style</span>
        <div className="seg">
          {["institutional", "editorial", "terminal"].map((key) => (
            <button key={key} className={state.chartStyle === key ? "on" : ""} onClick={() => set({ chartStyle: key })}>{key}</button>
          ))}
        </div>
      </label>
      <label><span>Density</span>
        <div className="seg">
          {["comfortable", "compact"].map((key) => (
            <button key={key} className={state.density === key ? "on" : ""} onClick={() => set({ density: key })}>{key}</button>
          ))}
        </div>
      </label>
    </div>
  );
}

function slugify(value) {
  return String(value).toLowerCase().replaceAll(" ", "_");
}

window.App = App;
ReactDOM.createRoot(document.getElementById("root")).render(<App />);

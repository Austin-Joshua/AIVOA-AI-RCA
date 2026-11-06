import { chromium } from '@playwright/test';

// Helper for human-like character-by-character typing
async function typeHuman(locator, text, delayMs = 30) {
  await locator.focus();
  try {
    await locator.clear();
  } catch {
    // ignore if not clearable
  }
  await locator.pressSequentially(text, { delay: delayMs });
}

async function runAutoDemo() {
  console.log('================================================================');
  console.log('🚀 AIVOA.AI — Complete AI-Powered RCA Showcase (Fullscreen)');
  console.log('================================================================');
  
  // Launch Chrome in true fullscreen maximizing user display
  const browser = await chromium.launch({
    headless: false,
    slowMo: 300,
    args: [
      '--start-maximized',
      '--start-fullscreen',
      '--disable-infobars',
      '--no-default-browser-check',
      '--disable-notifications',
    ],
  });

  // viewport: null ensures the browser expands to 100% of the screen with no letterboxing
  const context = await browser.newContext({
    viewport: null,
  });

  const page = await context.newPage();

  console.log('👉 [Setup] Hard-refreshing website and resetting all active state...');
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
  
  // Hard reset client storage to ensure fresh, zero ongoing processes state
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  // ── Scene 1: Sign in as Lead Investigator (with visible typing) ────────────
  console.log('👉 [Scene 1] Signing in as Dr. Sarah Lin (Lead Investigator)...');
  const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
  if (await usernameInput.isVisible().catch(() => false)) {
    await typeHuman(usernameInput, 'lead_investigator', 35);
    await page.waitForTimeout(300);
    const passwordInput = page.locator('form input[placeholder="Enter password"]');
    await typeHuman(passwordInput, 'AivoaPass2026!', 30);
    await page.waitForTimeout(500);
    await page.click('form button[type="submit"]:has-text("Sign In")');
    await page.waitForTimeout(2000);
  }

  // ── Scene 2: Load Paracetamol API Crystallization Scenario ─────────────────
  const startDemoBtn = page.locator('button:has-text("Start Paracetamol Demo Scenario")');
  if (await startDemoBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 2] Loading Paracetamol API Crystallization Demo Scenario...');
    await startDemoBtn.click();
    await page.waitForTimeout(2500);
  }

  // ── Scene 3: Showcase Light / Dark Mode Toggle Feature ─────────────────────
  console.log('👉 [Scene 3] Demonstrating Light / Dark Mode Theme Toggle...');
  const themeToggleBtn = page.locator('header button[aria-label*="mode"]').first();
  if (await themeToggleBtn.isVisible().catch(() => false)) {
    await themeToggleBtn.click();
    console.log('🌙 Switched to Dark Mode (showing dark cGMP styling)...');
    await page.waitForTimeout(2200);
    await themeToggleBtn.click();
    console.log('☀️ Switched back to Light Mode...');
    await page.waitForTimeout(1500);
  }

  // ── Scene 4: Comprehensive AI Copilot Utilization ──────────────────────────
  console.log('👉 [Scene 4] Engaging AI Copilot: Interactive Investigation & Reasoning...');

  // 4a. Live Copilot Chat: Asking Grounded Investigation Questions
  const chatTextarea = page.locator('textarea[placeholder*="Type incident report"]');
  if (await chatTextarea.isVisible().catch(() => false)) {
    console.log('...Typing investigation query into AI Copilot...');
    await chatTextarea.scrollIntoViewIfNeeded();
    await typeHuman(
      chatTextarea,
      'What was the peak temperature reached on reactor CR-104 and which valve failed?',
      25
    );
    await page.waitForTimeout(500);
    const sendBtn = page.locator('button[title="Send to Copilot"]');
    if (await sendBtn.isVisible().catch(() => false)) {
      await sendBtn.click();
      console.log('...Waiting for AI Copilot grounded response with citations...');
      await page.waitForTimeout(4000);
    }

    // 4b. Ask Follow-up Question for CAPA Guidance
    if (await chatTextarea.isVisible().catch(() => false)) {
      console.log('...Typing follow-up query for CAPA guidance...');
      await typeHuman(
        chatTextarea,
        'What corrective action is recommended for the CV-104 cooling valve failure?',
        25
      );
      await page.waitForTimeout(500);
      if (await sendBtn.isVisible().catch(() => false)) {
        await sendBtn.click();
        console.log('...Waiting for AI Copilot CAPA synthesis...');
        await page.waitForTimeout(4000);
      }
    }
  }

  // 4c. Copilot Document Intake Tab (AI Extraction Workflow)
  console.log('👉 [Scene 4c] Switching to Copilot Intake Tab (AI Document Extraction)...');
  const intakeTab = page.locator('button:has-text("Intake")').first();
  if (await intakeTab.isVisible().catch(() => false)) {
    await intakeTab.click();
    await page.waitForTimeout(1500);

    // Switch to Incident Text Mode
    const textModeBtn = page.locator('button:has-text("Incident Text")').first();
    if (await textModeBtn.isVisible().catch(() => false)) {
      await textModeBtn.click();
      await page.waitForTimeout(800);
    }

    // Click "Load Demo (DEV-2026-104)"
    const loadDemoBtn = page.locator('button:has-text("Load Demo (DEV-2026-104)")').first();
    if (await loadDemoBtn.isVisible().catch(() => false)) {
      console.log('...Loading raw manufacturing deviation report into intake text box...');
      await loadDemoBtn.click();
      await page.waitForTimeout(1200);
    }

    // Click "Extract Structured Information via Groq"
    const extractBtn = page.locator('button:has-text("Extract Structured Information via Groq")').first();
    if (await extractBtn.isVisible().catch(() => false)) {
      console.log('...Running LangGraph structured extraction via Groq...');
      await extractBtn.click();
      await page.waitForTimeout(5500);
    }

    // Review extracted fields and click Apply
    const acceptAllBtn = page.locator('button:has-text("Select All")').first();
    if (await acceptAllBtn.isVisible().catch(() => false)) {
      await acceptAllBtn.click();
      await page.waitForTimeout(800);
    }

    const applyFieldsBtn = page.locator('button:has-text("Apply")').filter({ hasText: /Approved Fields/i }).first();
    if (await applyFieldsBtn.isVisible().catch(() => false)) {
      console.log('...Applying AI-extracted fields to investigation form...');
      await applyFieldsBtn.click();
      await page.waitForTimeout(2000);
    }
  }

  // 4d. Copilot Evidence Gaps Tab
  console.log('👉 [Scene 4d] Inspecting Copilot Evidence Gaps Tab...');
  const gapsTab = page.locator('button:has-text("Gaps")').first();
  if (await gapsTab.isVisible().catch(() => false)) {
    await gapsTab.click();
    await page.waitForTimeout(2000);
  }

  // 4e. Copilot RCA Engine Tab (LangGraph Multi-Methodology Engine)
  console.log('👉 [Scene 4e] Demonstrating LangGraph RCA Engine Tab...');
  const rcaTab = page.locator('button:has-text("RCA")').first();
  if (await rcaTab.isVisible().catch(() => false)) {
    await rcaTab.click();
    await page.waitForTimeout(1500);

    const genRcaBtn = page.locator('button:has-text("Generate Full RCA & CAPA Package")').first();
    if (await genRcaBtn.isVisible().catch(() => false)) {
      console.log('...Triggering LangGraph multi-methodology RCA Engine...');
      await genRcaBtn.click();
      await page.waitForTimeout(6000);
    }

    const applyAllRcaBtn = page.locator('button:has-text("Apply All Proposals")').first();
    if (await applyAllRcaBtn.isVisible().catch(() => false)) {
      await applyAllRcaBtn.click();
      await page.waitForTimeout(1500);
    }
  }

  // 4f. Copilot Workflow Trace Tab (12 LangGraph StateGraph Nodes)
  console.log('👉 [Scene 4f] Inspecting LangGraph Workflow Trace...');
  const traceTab = page.locator('button:has-text("Trace")').first();
  if (await traceTab.isVisible().catch(() => false)) {
    await traceTab.click();
    await page.waitForTimeout(2500);
  }

  // Return to Chat tab
  const chatTab = page.locator('button:has-text("Chat")').first();
  if (await chatTab.isVisible().catch(() => false)) {
    await chatTab.click();
    await page.waitForTimeout(1000);
  }

  // ── Scene 5: Incident Intake & Deviation Parameters Form ───────────────────
  console.log('👉 [Scene 5] Reviewing Incident Intake & Deviation parameters in center form...');
  const deviationSec = page.locator('#section-deviation');
  if (await deviationSec.isVisible().catch(() => false)) {
    await deviationSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2000);
  }

  // ── Scene 6: Evidence & Timeline + Verification Modal ──────────────────────
  console.log('👉 [Scene 6] Navigating to Evidence & Timeline section...');
  const stage2Btn = page.locator('button:has-text("2. Evidence & Timeline")');
  if (await stage2Btn.isVisible().catch(() => false)) {
    await stage2Btn.click();
    await page.waitForTimeout(1800);
  }

  // Formally verify empirical evidence through the verification modal
  const verifyBtn = page.locator('button:has-text("Verify")').first();
  if (await verifyBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 6] Opening Evidence Verification modal...');
    await verifyBtn.click();
    await page.waitForTimeout(1000);

    const notesInput = page.locator('textarea[placeholder*="Examined physical batch log"]');
    if (await notesInput.isVisible().catch(() => false)) {
      console.log('👉 [Scene 6] Typing verification justification notes...');
      await typeHuman(
        notesInput,
        'Cross-referenced SCADA historian tag TI-104 with physical calibration sticker CAL-2026-88 on reactor jacket.',
        25
      );
      await page.waitForTimeout(500);
    }

    const signVerifyBtn = page.locator('button:has-text("Sign & Verify Record")');
    if (await signVerifyBtn.isVisible().catch(() => false)) {
      console.log('👉 [Scene 6] Signing and verifying evidence record...');
      await signVerifyBtn.click();
      await page.waitForTimeout(1800);
    }
  }

  // ── Scene 7: 5-Whys & Fishbone Diagram ────────────────────────────────────
  console.log('👉 [Scene 7] Navigating to 5-Whys & Fishbone section...');
  const stage3Btn = page.locator('button:has-text("3. 5-Whys & Fishbone")');
  if (await stage3Btn.isVisible().catch(() => false)) {
    await stage3Btn.click();
    await page.waitForTimeout(1500);
  }

  const genBtn = page.locator('button:has-text("Generate 5 Whys & Fishbone with AI")').first();
  if (await genBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 7] Triggering AI 5-Whys & Fishbone causality generation...');
    await genBtn.click();
    console.log('...Waiting for causality network synthesis...');
    await page.waitForTimeout(5500);
  }

  // Link Evidence to Why #1
  const linkEvBtn = page.locator('button:has-text("Link Evidence")').first();
  if (await linkEvBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 7] Linking verified SCADA evidence to Why Step #1...');
    await linkEvBtn.click();
    await page.waitForTimeout(1000);

    const relExplInput = page.locator('textarea[placeholder*="substantiates or refutes"]');
    if (await relExplInput.isVisible().catch(() => false)) {
      await typeHuman(
        relExplInput,
        'Direct SCADA telemetry substantiates pneumatic pressure loss causal node.',
        25
      );
      await page.waitForTimeout(500);
    }

    const confirmLinkBtn = page.locator('div[role="dialog"] button:has-text("Link Evidence"), form button:has-text("Link Evidence")');
    if (await confirmLinkBtn.isVisible().catch(() => false)) {
      await confirmLinkBtn.click();
      await page.waitForTimeout(1500);
    } else {
      const cancelBtn = page.locator('div[role="dialog"] button:has-text("Cancel")');
      if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
    }
  }

  // Scroll to Fishbone Diagram and demonstrate View Switcher
  console.log('👉 [Scene 7] Reviewing Ishikawa 6M Fishbone Diagram & Grid views...');
  const fishboneSec = page.locator('#section-fishbone');
  if (await fishboneSec.isVisible().catch(() => false)) {
    await fishboneSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1500);

    // Switch to 6Ms Grid View
    const gridViewBtn = page.locator('button:has-text("6Ms Grid")');
    if (await gridViewBtn.isVisible().catch(() => false)) {
      await gridViewBtn.click();
      console.log('...Switched to 6Ms Grid categorization view...');
      await page.waitForTimeout(2000);
    }

    // Switch back to Diagram View
    const diagViewBtn = page.locator('button:has-text("Diagram View")');
    if (await diagViewBtn.isVisible().catch(() => false)) {
      await diagViewBtn.click();
      console.log('...Switched back to visual Fishbone diagram...');
      await page.waitForTimeout(2000);
    }
  }

  // ── Scene 8: CAPA Recommendations ────────────────────────────────────────
  console.log('👉 [Scene 8] Navigating to CAPA Recommendations section...');
  const stage4Btn = page.locator('button:has-text("4. CAPA Recommendations")');
  if (await stage4Btn.isVisible().catch(() => false)) {
    await stage4Btn.click();
    await page.waitForTimeout(2500);
  }

  // ── Scene 9: Separation of Duties & 21 CFR Part 11 Gate ───────────────────
  console.log('👉 [Scene 9] Viewing 21 CFR Part 11 Gate (Investigator blocked from self-approval)...');
  const stage5Btn = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await stage5Btn.isVisible().catch(() => false)) {
    await stage5Btn.click();
    await page.waitForTimeout(2200);
  }

  // ── Scene 10: Sign Out & Move to Second Login (QA Director) ───────────────
  console.log('👉 [Scene 10] Signing out from Lead Investigator...');
  const userBtn = page.locator('button[aria-label*="User account"]');
  if (await userBtn.isVisible().catch(() => false)) {
    await userBtn.click();
    await page.waitForTimeout(600);
    const signOutBtn = page.locator('button:has-text("Sign Out")');
    if (await signOutBtn.isVisible().catch(() => false)) {
      await signOutBtn.click();
      await page.waitForTimeout(1500);
    }
  }

  // Second Login: Sign in as QA Director (with visible human typing)
  console.log('👉 [Scene 10] Signing in as Dr. Elena Rostova (QA Director)...');
  const userIn = page.locator('form input[placeholder="Enter cGMP username"]');
  if (await userIn.isVisible().catch(() => false)) {
    await typeHuman(userIn, 'qa_director', 35);
    await page.waitForTimeout(300);
    const passIn = page.locator('form input[placeholder="Enter password"]');
    await typeHuman(passIn, 'AivoaPass2026!', 30);
    await page.waitForTimeout(500);
    await page.click('form button[type="submit"]:has-text("Sign In")');
    await page.waitForTimeout(2000);
  }

  // ── Scene 11: QA Director Electronic Signature (21 CFR Part 11) ───────────
  console.log('👉 [Scene 11] Navigating to Stage 5 for formal QA approval...');
  const stage5BtnQA = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await stage5BtnQA.isVisible().catch(() => false)) {
    await stage5BtnQA.click();
    await page.waitForTimeout(1500);
  }

  // Type QA rationale character-by-character
  const commentsInput = page.locator('textarea[placeholder*="scientific justification"]');
  if (await commentsInput.isVisible().catch(() => false)) {
    console.log('👉 [Scene 11] Typing formal scientific justification and closure rationale...');
    await typeHuman(
      commentsInput,
      'Formally reviewed 5-Whys causality chain and CV-104 pneumatic telemetry. Confirmed actuator seal failure mode and approved CAPA overhaul plan under cGMP guidelines.',
      25
    );
    await page.waitForTimeout(1200);
  }

  // Submit Electronic Signature
  const approveBtn = page.locator('button:has-text("Sign & Approve Investigation")');
  if (await approveBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 11] Executing 21 CFR Part 11 Electronic Signature...');
    await approveBtn.click();
    await page.waitForTimeout(3000);
  }

  // ── Scene 12: ALCOA+ Audit Trail Dossier ──────────────────────────────────
  console.log('👉 [Scene 12] Opening Audit Trail Dossier...');
  const auditBtn = page.locator('button[aria-label="View audit trail"]');
  if (await auditBtn.isVisible().catch(() => false)) {
    await auditBtn.click();
    await page.waitForTimeout(3500);
    // Dismiss audit modal cleanly with Escape key
    await page.keyboard.press('Escape');
    await page.waitForTimeout(1000);
  }

  // ── Final Scene: Completion Pop-up Message for Video Recording ─────────────
  console.log('👉 [Scene 13] Displaying Showcase Completion Banner on screen...');
  await page.evaluate(() => {
    const existing = document.getElementById('demo-completion-popup');
    if (existing) existing.remove();

    const banner = document.createElement('div');
    banner.id = 'demo-completion-popup';
    banner.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: 9999999;
      background: rgba(15, 23, 42, 0.96);
      backdrop-filter: blur(20px);
      color: white;
      padding: 40px 52px;
      border-radius: 24px;
      box-shadow: 0 25px 60px -12px rgba(0, 0, 0, 0.85), 0 0 0 2px #22c55e;
      text-align: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 640px;
      width: 90%;
      animation: popIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    `;

    banner.innerHTML = `
      <style>
        @keyframes popIn {
          0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
          100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        @keyframes pulseRec {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.04); }
        }
      </style>
      <div style="font-size: 52px; margin-bottom: 12px;">✅</div>
      <h2 style="font-size: 26px; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 8px; color: #4ade80;">
        SHOWCASE DEMO COMPLETE!
      </h2>
      <p style="font-size: 15px; color: #cbd5e1; margin-bottom: 22px; line-height: 1.5;">
        All cGMP RCA capabilities demonstrated: 5 stages, deep AI Copilot integration (Intake, Chat, Gaps, RCA, Trace), light/dark themes, role segregation, and 21 CFR Part 11 sign-off.
      </p>
      <div style="
        background: #dc2626;
        color: white;
        padding: 14px 28px;
        border-radius: 12px;
        font-weight: 800;
        font-size: 18px;
        letter-spacing: 0.03em;
        display: inline-flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 10px 25px -5px rgba(220, 38, 38, 0.5);
        animation: pulseRec 1.5s infinite;
      ">
        <span style="display: inline-block; width: 14px; height: 14px; background: white; border-radius: 50%;"></span>
        YOU CAN STOP YOUR SCREEN RECORDING NOW!
      </div>
    `;
    document.body.appendChild(banner);
  });

  console.log('================================================================');
  console.log('🎉 Showcase Walkthrough Complete! Holding open for 25 seconds...');
  console.log('🔴 YOU CAN STOP YOUR SCREEN RECORDING NOW!');
  console.log('================================================================');
  await page.waitForTimeout(25000);

  await browser.close();
}

runAutoDemo().catch(console.error);

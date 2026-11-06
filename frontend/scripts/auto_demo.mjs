import { chromium } from '@playwright/test';

// Helper for human-like character-by-character typing
async function typeHuman(locator, text, delayMs = 35) {
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
  console.log('🚀 AIVOA.AI — True Fullscreen Automated Showcase Video Recording');
  console.log('================================================================');
  
  // Launch Chrome in true fullscreen maximizing user display
  const browser = await chromium.launch({
    headless: false,
    slowMo: 400,
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
    await typeHuman(usernameInput, 'lead_investigator', 40);
    await page.waitForTimeout(400);
    const passwordInput = page.locator('form input[placeholder="Enter password"]');
    await typeHuman(passwordInput, 'AivoaPass2026!', 35);
    await page.waitForTimeout(600);
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

  // ── Scene 2b: Demonstrate Live AI Chat with Self-Typing ────────────────────
  console.log('👉 [Scene 2] Typing interactive investigation query in AI Copilot...');
  const chatTextarea = page.locator('textarea[placeholder*="Type incident report"]');
  if (await chatTextarea.isVisible().catch(() => false)) {
    await chatTextarea.scrollIntoViewIfNeeded();
    await typeHuman(
      chatTextarea,
      'Analyze root cause for temperature excursion to 86.4°C on reactor CR-104 during Paracetamol crystallization.',
      30
    );
    await page.waitForTimeout(800);
    const sendBtn = page.locator('button[title="Send to Copilot"]');
    if (await sendBtn.isVisible().catch(() => false)) {
      await sendBtn.click();
      console.log('...Waiting for AI Copilot reasoning and field extraction...');
      await page.waitForTimeout(4000);
    }
  }

  // Review Center Form (Deviation Details)
  console.log('👉 [Scene 2] Reviewing Incident Intake & Deviation parameters...');
  const deviationSec = page.locator('#section-deviation');
  if (await deviationSec.isVisible().catch(() => false)) {
    await deviationSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2200);
  }

  // ── Scene 3: Evidence & Timeline ──────────────────────────────────────────
  console.log('👉 [Scene 3] Navigating to Evidence & Timeline section...');
  const stage2Btn = page.locator('button:has-text("2. Evidence & Timeline")');
  if (await stage2Btn.isVisible().catch(() => false)) {
    await stage2Btn.click();
    await page.waitForTimeout(2000);
  }

  // Click Verify on empirical evidence
  const verifyBtn = page.locator('button:has-text("Verify")').first();
  if (await verifyBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 3] Verifying empirical SCADA evidence record...');
    await verifyBtn.click();
    await page.waitForTimeout(1500);
  }

  // ── Scene 4: 5-Whys & Fishbone Diagram ────────────────────────────────────
  console.log('👉 [Scene 4] Navigating to 5-Whys & Fishbone section...');
  const stage3Btn = page.locator('button:has-text("3. 5-Whys & Fishbone")');
  if (await stage3Btn.isVisible().catch(() => false)) {
    await stage3Btn.click();
    await page.waitForTimeout(1500);
  }

  const genBtn = page.locator('button:has-text("Generate 5 Whys & Fishbone with AI")').first();
  if (await genBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 4] Triggering AI 5-Whys & Fishbone generation...');
    await genBtn.click();
    console.log('...Waiting for causality network synthesis...');
    await page.waitForTimeout(6000);
  }

  // Link Evidence to Why #1
  const linkEvBtn = page.locator('button:has-text("Link Evidence")').first();
  if (await linkEvBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 4] Linking verified SCADA evidence to Why Step #1...');
    await linkEvBtn.click();
    await page.waitForTimeout(1200);

    const evSelect = page.locator('select').filter({ hasText: /SCADA|Select Evidence/i }).first();
    if (await evSelect.isVisible().catch(() => false)) {
      const options = await evSelect.locator('option').all();
      if (options.length > 1) {
        await evSelect.selectOption({ index: 1 });
      }
    }
    await page.waitForTimeout(800);
    const confirmLinkBtn = page.locator('div[role="dialog"] button:has-text("Link Evidence")');
    if (await confirmLinkBtn.isVisible().catch(() => false)) {
      await confirmLinkBtn.click();
      await page.waitForTimeout(1500);
    } else {
      const cancelBtn = page.locator('div[role="dialog"] button:has-text("Cancel")');
      if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
    }
  }

  // Scroll to Fishbone Diagram
  console.log('👉 [Scene 4] Reviewing Ishikawa 6M Fishbone Diagram...');
  const fishboneSec = page.locator('#section-fishbone');
  if (await fishboneSec.isVisible().catch(() => false)) {
    await fishboneSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2500);
  }

  // ── Scene 5: CAPA Recommendations ────────────────────────────────────────
  console.log('👉 [Scene 5] Navigating to CAPA Recommendations section...');
  const stage4Btn = page.locator('button:has-text("4. CAPA Recommendations")');
  if (await stage4Btn.isVisible().catch(() => false)) {
    await stage4Btn.click();
    await page.waitForTimeout(2500);
  }

  // ── Scene 6: Separation of Duties & QA Sign-Off ───────────────────────────
  console.log('👉 [Scene 6] Viewing 21 CFR Part 11 Gate (Investigator blocked from self-approval)...');
  const stage5Btn = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await stage5Btn.isVisible().catch(() => false)) {
    await stage5Btn.click();
    await page.waitForTimeout(2500);
  }

  // Sign out from Investigator
  console.log('👉 [Scene 6] Signing out to switch to QA Director persona...');
  const userBtn = page.locator('button[aria-label*="User account"]');
  if (await userBtn.isVisible().catch(() => false)) {
    await userBtn.click();
    await page.waitForTimeout(800);
    const signOutBtn = page.locator('button:has-text("Sign Out")');
    if (await signOutBtn.isVisible().catch(() => false)) {
      await signOutBtn.click();
      await page.waitForTimeout(1500);
    }
  }

  // Sign in as QA Director (with visible typing)
  console.log('👉 [Scene 6] Signing in as Dr. Elena Rostova (QA Director)...');
  const userIn = page.locator('form input[placeholder="Enter cGMP username"]');
  if (await userIn.isVisible().catch(() => false)) {
    await typeHuman(userIn, 'qa_director', 40);
    await page.waitForTimeout(400);
    const passIn = page.locator('form input[placeholder="Enter password"]');
    await typeHuman(passIn, 'AivoaPass2026!', 35);
    await page.waitForTimeout(600);
    await page.click('form button[type="submit"]:has-text("Sign In")');
    await page.waitForTimeout(2000);
  }

  // Navigate to Approval section
  console.log('👉 [Scene 6] Navigating to Stage 5 for formal QA approval...');
  const stage5BtnQA = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await stage5BtnQA.isVisible().catch(() => false)) {
    await stage5BtnQA.click();
    await page.waitForTimeout(1500);
  }

  // Type QA rationale character-by-character
  const commentsInput = page.locator('textarea[placeholder*="scientific justification"]');
  if (await commentsInput.isVisible().catch(() => false)) {
    console.log('👉 [Scene 6] Typing formal scientific justification and closure rationale...');
    await typeHuman(
      commentsInput,
      'Formally reviewed 5-Whys causality chain and CV-104 pneumatic telemetry. Confirmed actuator seal failure mode and approved CAPA overhaul plan under cGMP guidelines.',
      28
    );
    await page.waitForTimeout(1500);
  }

  // Submit Electronic Signature
  const approveBtn = page.locator('button:has-text("Sign & Approve Investigation")');
  if (await approveBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 6] Executing 21 CFR Part 11 Electronic Signature...');
    await approveBtn.click();
    await page.waitForTimeout(3000);
  }

  // Open Audit Trail
  console.log('👉 [Scene 6] Opening Audit Trail Dossier...');
  const auditBtn = page.locator('button[aria-label="View audit trail"]');
  if (await auditBtn.isVisible().catch(() => false)) {
    await auditBtn.click();
    await page.waitForTimeout(4000);
  }

  console.log('================================================================');
  console.log('🎉 Fullscreen Automated Walkthrough Complete! Holding for 20s...');
  console.log('================================================================');
  await page.waitForTimeout(20000);

  await browser.close();
}

runAutoDemo().catch(console.error);

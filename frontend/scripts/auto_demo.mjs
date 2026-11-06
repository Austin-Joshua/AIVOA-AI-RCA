import { chromium } from '@playwright/test';

async function runAutoDemo() {
  console.log('================================================================');
  console.log('🚀 AIVOA.AI — Automated Product Showcase Demo (Screen Recording)');
  console.log('================================================================');
  
  const browser = await chromium.launch({
    headless: false,
    slowMo: 800,
    args: ['--start-maximized'],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();

  console.log('👉 [Scene 1] Navigating to http://127.0.0.1:5173...');
  await page.goto('http://127.0.0.1:5173');
  await page.waitForTimeout(1500);

  // 1. Check Authentication
  const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
  if (await usernameInput.isVisible().catch(() => false)) {
    console.log('👉 [Scene 1] Signing in as Dr. Sarah Lin (Lead Investigator)...');
    await usernameInput.fill('lead_investigator');
    await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
    await page.click('form button[type="submit"]:has-text("Sign In")');
    await page.waitForTimeout(2000);
  }

  // 2. Start Demo Scenario
  const startDemoBtn = page.locator('button:has-text("Start Paracetamol Demo Scenario")');
  if (await startDemoBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 2] Loading Paracetamol API Crystallization Demo Scenario...');
    await startDemoBtn.click();
    await page.waitForTimeout(2500);
  }

  // 3. Review Center Form (Deviation Details)
  console.log('👉 [Scene 2] Reviewing Incident Intake & Deviation parameters...');
  const deviationSec = page.locator('#section-deviation');
  if (await deviationSec.isVisible().catch(() => false)) {
    await deviationSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2000);
  }

  // 4. Evidence & Timeline
  console.log('👉 [Scene 3] Navigating to Evidence & Timeline section...');
  const stage2Btn = page.locator('button:has-text("2. Evidence & Timeline")');
  if (await stage2Btn.isVisible().catch(() => false)) {
    await stage2Btn.click();
    await page.waitForTimeout(1500);
  }

  // Verify evidence if unverified
  const verifyBtn = page.locator('button:has-text("Verify")').first();
  if (await verifyBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 3] Verifying empirical evidence record...');
    await verifyBtn.click();
    await page.waitForTimeout(1500);
  }

  // 5. 5-Whys & Fishbone
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

  // Scroll to Fishbone Diagram
  console.log('👉 [Scene 4] Reviewing Ishikawa 6M Fishbone Diagram...');
  const fishboneSec = page.locator('#section-fishbone');
  if (await fishboneSec.isVisible().catch(() => false)) {
    await fishboneSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2500);
  }

  // 6. CAPA Section
  console.log('👉 [Scene 5] Navigating to CAPA Recommendations section...');
  const stage4Btn = page.locator('button:has-text("4. CAPA Recommendations")');
  if (await stage4Btn.isVisible().catch(() => false)) {
    await stage4Btn.click();
    await page.waitForTimeout(2500);
  }

  // 7. Approval Section (Investigator View)
  console.log('👉 [Scene 6] Viewing 21 CFR Part 11 Gate (Investigator blocked from self-approval)...');
  const stage5Btn = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await stage5Btn.isVisible().catch(() => false)) {
    await stage5Btn.click();
    await page.waitForTimeout(2500);
  }

  // 8. Sign out from Investigator
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

  // 9. Sign in as QA Director
  console.log('👉 [Scene 6] Signing in as Dr. Elena Rostova (QA Director)...');
  const userIn = page.locator('form input[placeholder="Enter cGMP username"]');
  if (await userIn.isVisible().catch(() => false)) {
    await userIn.fill('qa_director');
    await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
    await page.click('form button[type="submit"]:has-text("Sign In")');
    await page.waitForTimeout(2000);
  }

  // 10. Navigate to Approval and Sign Off
  console.log('👉 [Scene 6] Navigating to Stage 5 for formal QA approval...');
  const stage5BtnQA = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await stage5BtnQA.isVisible().catch(() => false)) {
    await stage5BtnQA.click();
    await page.waitForTimeout(1500);
  }

  const commentsInput = page.locator('textarea[placeholder*="scientific justification"]');
  if (await commentsInput.isVisible().catch(() => false)) {
    await commentsInput.fill('Formally reviewed 5-Whys causality chain and valve telemetry evidence. Confirmed CV-104 pneumatic actuator seal failure mode and approved CAPA overhaul plan.');
    await page.waitForTimeout(1500);
  }

  const approveBtn = page.locator('button:has-text("Sign & Approve Investigation")');
  if (await approveBtn.isVisible().catch(() => false)) {
    console.log('👉 [Scene 6] Submitting 21 CFR Part 11 Electronic Signature...');
    await approveBtn.click();
    await page.waitForTimeout(3000);
  }

  // 11. Open Audit Trail
  console.log('👉 [Scene 6] Opening Audit Trail Dossier...');
  const auditBtn = page.locator('button[aria-label="View audit trail"]');
  if (await auditBtn.isVisible().catch(() => false)) {
    await auditBtn.click();
    await page.waitForTimeout(4000);
  }

  console.log('================================================================');
  console.log('🎉 Showcase Walkthrough Complete! Holding open for 15 seconds...');
  console.log('================================================================');
  await page.waitForTimeout(15000);

  await browser.close();
}

runAutoDemo().catch(console.error);

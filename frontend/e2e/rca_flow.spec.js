import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const screensDir = path.resolve(process.cwd(), '..', 'docs', 'screens');
if (!fs.existsSync(screensDir)) {
  fs.mkdirSync(screensDir, { recursive: true });
}

test('Full RCA Lifecycle: Intake, AI Extraction, 6Ms Fishbone, Root Cause, CAPA, Audit Trail', async ({ page }) => {
  // Capture unhandled console errors
  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const txt = msg.text();
      // Ignore favicon or upstream provider rate-limiting status 429 network logs
      if (!txt.includes('favicon.ico') && !txt.includes('429 (Too Many Requests)')) {
        consoleErrors.push(txt);
      }
    }
  });

  // Set 1440x900 viewport
  await page.setViewportSize({ width: 1440, height: 900 });

  console.log('Step 1: Navigating to http://127.0.0.1:5173...');
  await page.goto('http://127.0.0.1:5173');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  console.log('Step 2: Checking authentication...');
  const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
  if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('Logging in as lead_investigator...');
    await usernameInput.fill('lead_investigator');
    await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
    await page.click('form button[type="submit"]:has-text("Sign In")');
    await page.waitForTimeout(1500);
  }

  // Capture Screen 1: Authenticated Workspace
  console.log('Capturing Screen 1: Workspace...');
  await page.screenshot({ path: path.join(screensDir, '01_login_and_workspace.png') });

  // Step 3: Check if an investigation is loaded or start demo / create new
  console.log('Step 3: Ensuring fresh investigation for demo flow...');
  const startDemoBtn = page.locator('button:has-text("Start Paracetamol Demo Scenario")');
  if (await startDemoBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    console.log('Clicking Start Paracetamol Demo Scenario...');
    await startDemoBtn.click();
    await page.waitForTimeout(2000);
  } else {
    console.log('Opening fresh investigation for RCA flow...');
    await page.click('button:has-text("New RCA")');
    await page.fill('input[placeholder*="Paracetamol API Crystallization"]', 'Paracetamol API Thermal Excursion E2E');
    await page.click('div[role="dialog"] button:has-text("Open Investigation")');
    await page.waitForTimeout(2000);
  }

  // Step 4: Check dynamic AI model config against /api/v1/config/ai in active workspace
  console.log('Step 4: Checking AI model config in UI...');
  const token = await page.evaluate(() => localStorage.getItem('aivoa_token'));
  const aiConfigRes = await page.request.get('http://127.0.0.1:8000/api/v1/config/ai', {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  expect(aiConfigRes.status()).toBe(200);
  const aiConfig = await aiConfigRes.json();
  console.log('Active AI model reported by backend:', aiConfig.model);
  const modelBadge = page.getByText(aiConfig.model).first();
  await expect(modelBadge).toBeVisible();

  // Step 5: Copilot Chat Intake
  console.log('Step 5: Opening Copilot Chat...');
  const chatTab = page.locator('button:has-text("Chat")');
  if (await chatTab.isVisible({ timeout: 1500 }).catch(() => false)) {
    await chatTab.click();
    await page.waitForTimeout(500);
  }

  const loadScenarioBtn = page.locator('button:has-text("Load Paracetamol Scenario")');
  if (await loadScenarioBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('Loading Paracetamol Scenario in chat...');
    await loadScenarioBtn.click();
    await page.waitForTimeout(800);

    const sendBtn = page.locator('button[title="Send to Copilot"]');
    await expect(sendBtn).toBeEnabled({ timeout: 2000 });
    console.log('Sending to Copilot...');
    await sendBtn.click();
    await page.waitForTimeout(5000);
  }

  // Capture Screen 2: Incident Intake & Copilot Extraction
  console.log('Capturing Screen 2: Incident Intake & Copilot Extraction...');
  await page.screenshot({ path: path.join(screensDir, '02_incident_intake_copilot.png') });

  // Step 6: Verify Deviation Form & Non-Fabricated Deviation Number
  console.log('Step 6: Verifying Deviation Form...');
  const batchField = page.locator('#section-deviation').getByText('Batch Number');
  await expect(batchField).toBeVisible();

  // Deviation number must be DEV-2026-104 (from scenario) and never invented
  const deviationNumEl = page.locator('#section-deviation').getByText('DEV-2026-104');
  await expect(deviationNumEl).toBeVisible({ timeout: 15000 });

  // Commit Form if present
  const commitBtn = page.locator('#section-deviation button:has-text("Commit Form")');
  if (await commitBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    console.log('Committing deviation form...');
    await commitBtn.click();
    await page.waitForTimeout(800);
  }

  // Capture Screen 3: Deviation Form Committed
  console.log('Capturing Screen 3: Deviation Form Committed...');
  await page.screenshot({ path: path.join(screensDir, '03_deviation_form_committed.png') });

  // Step 7: Fishbone Section & Generate AI Button
  console.log('Step 7: Navigating to 5-Whys & Fishbone...');
  const fishboneNavBtn = page.locator('button:has-text("3. 5-Whys & Fishbone")');
  await fishboneNavBtn.click();
  await page.waitForTimeout(1000);

  const fishboneSection = page.locator('#section-fishbone');
  await expect(fishboneSection).toBeVisible();

  // Check for AI Generation CTA if empty or present
  const generateAiBtn = page.locator('button:has-text("Generate 5 Whys & Fishbone with AI")').first();
  if (await generateAiBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    console.log('Triggering AI 5-Whys & Fishbone generation...');
    await generateAiBtn.click();
    await page.waitForTimeout(3000);
  }

  // Verify Environment (Facility / HVAC) label in Fishbone
  const envLabel = page.locator('text=Environment (Facility / HVAC)');
  await expect(envLabel).toBeVisible();

  // Capture Screen 4: Interactive SVG Fishbone Diagram
  console.log('Capturing Screen 4: Interactive SVG Fishbone Diagram...');
  await page.screenshot({ path: path.join(screensDir, '04_fishbone_interactive_diagram.png') });

  // Step 8: CAPA Recommendations
  console.log('Step 8: Navigating to CAPA Recommendations...');
  const capaNavBtn = page.locator('button:has-text("4. CAPA Recommendations")');
  await capaNavBtn.click();
  await page.waitForTimeout(1000);

  const capaSection = page.locator('#section-capa');
  await expect(capaSection).toBeVisible();

  // Capture Screen 5: CAPA Program
  console.log('Capturing Screen 5: CAPA Program...');
  await page.screenshot({ path: path.join(screensDir, '05_root_cause_and_capa.png') });

  // Step 9: Approval Section - Verify empty rationale & no fake pre-fill
  console.log('Step 9: Navigating to Sign-Off & Approval...');
  const approvalNavBtn = page.locator('button:has-text("5. Review & Sign-Off")');
  if (await approvalNavBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await approvalNavBtn.click();
    await page.waitForTimeout(1000);

    const approvalSection = page.locator('#section-approval');
    await expect(approvalSection).toBeVisible();

    const rationaleTextarea = approvalSection.locator('textarea');
    // Must start EMPTY (no pre-filled justification)
    await expect(rationaleTextarea).toHaveValue('');

    // Must have placeholder "Full name and title" on approver input
    const approverInput = approvalSection.locator('input[placeholder="Full name and title"]');
    await expect(approverInput).toBeVisible();
  }

  // Step 10: Audit Trail Dossier
  console.log('Step 10: Opening Audit Trail Dossier...');
  const auditBtn = page.locator('header button:has-text("Audit")');
  await auditBtn.click();
  await page.waitForTimeout(1000);

  const auditModal = page.locator('text=Audit Trail Dossier');
  await expect(auditModal).toBeVisible();

  // Capture Screen 6: Audit Trail
  console.log('Capturing Screen 6: Audit Trail...');
  await page.screenshot({ path: path.join(screensDir, '06_audit_trail_verification.png') });

  const closeBtn = page.locator('button:has-text("Close")');
  if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await closeBtn.click();
    await page.waitForTimeout(500);
  }

  // Verify zero unhandled console errors
  console.log('Checking console errors:', consoleErrors);
  expect(consoleErrors).toEqual([]);

  console.log('E2E Test completed successfully with all Prompt F assertions verified!');
});

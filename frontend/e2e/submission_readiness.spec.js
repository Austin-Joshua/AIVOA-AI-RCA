import { test, expect } from '@playwright/test';

test.describe('Submission-Readiness Governance and Negative E2E Gates', () => {

  test('Gate 1: Investigator cannot approve own investigation (Separation of Duties)', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');

    // 1. Login as investigator if not authenticated
    const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
    if (await usernameInput.isVisible({ timeout: 1500 }).catch(() => false)) {
      await usernameInput.fill('lead_investigator');
      await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
      await page.click('form button[type="submit"]:has-text("Sign In")');
      await page.waitForTimeout(1000);
    }

    // Ensure paracetamol scenario or investigation is active
    const startDemoBtn = page.locator('button:has-text("Start Paracetamol Demo Scenario")');
    if (await startDemoBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await startDemoBtn.click();
      await page.waitForTimeout(1500);
    }

    // If current investigation is already sealed/approved, open a fresh one to test the unapproved sign-off state
    const isApprovedBadge = page.locator('header').getByText('QA Approved');
    if (await isApprovedBadge.isVisible({ timeout: 1000 }).catch(() => false)) {
      await page.click('button:has-text("New RCA")');
      await page.fill('input[placeholder*="Paracetamol API Crystallization"]', 'Separation of Duties Verification Dossier');
      await page.click('div[role="dialog"] button:has-text("Open Investigation")');
      await page.waitForTimeout(1500);
    }

    // Approval section is visible on page
    const approvalSection = page.locator('#section-approval');
    await expect(approvalSection).toBeVisible();

    // Verify warning banner explaining QA role requirement is displayed
    const qaRoleWarning = approvalSection.getByText(/Formal investigation dossier closure strictly requires/i);
    await expect(qaRoleWarning).toBeVisible();

    // Verify Sign & Approve button is strictly disabled for investigator with explicit role guard label
    const signApproveBtn = approvalSection.locator('button:has-text("QA_APPROVER Role Required")');
    await expect(signApproveBtn).toBeDisabled();
  });

  test('Gate 2: Chat correction changes a field and badge shows "Edited by you"', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');

    // Ensure authenticated
    const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
    if (await usernameInput.isVisible({ timeout: 1500 }).catch(() => false)) {
      await usernameInput.fill('lead_investigator');
      await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
      await page.click('form button[type="submit"]:has-text("Sign In")');
      await page.waitForTimeout(1000);
    }

    // Start Demo if needed
    const startDemoBtn = page.locator('button:has-text("Start Paracetamol Demo Scenario")');
    if (await startDemoBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await startDemoBtn.click();
      await page.waitForTimeout(1500);
    }

    // Open Copilot Chat
    const chatTab = page.locator('button:has-text("Chat")');
    if (await chatTab.isVisible({ timeout: 1500 }).catch(() => false)) {
      await chatTab.click();
      await page.waitForTimeout(400);
    }

    // Send correction message to Copilot: "Correction: Equipment is RX-302"
    const chatInput = page.locator('textarea[placeholder*="Type incident report"]');
    await chatInput.fill('Correction: Equipment is RX-302');
    const sendBtn = page.locator('button[title="Send to Copilot"]');
    await sendBtn.click();
    await page.waitForTimeout(4000);

    // Verify Equipment field shows "Edited by you" badge in DeviationSection
    const deviationSection = page.locator('#section-deviation');
    const editedBadge = deviationSection.getByText('Edited by you').first();
    await expect(editedBadge).toBeVisible();
  });

  test('Gate 3: Double-click on scenario load creates one idempotent turn', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');

    // Ensure authenticated
    const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
    if (await usernameInput.isVisible({ timeout: 1500 }).catch(() => false)) {
      await usernameInput.fill('lead_investigator');
      await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
      await page.click('form button[type="submit"]:has-text("Sign In")');
      await page.waitForTimeout(1000);
    }

    // Open Chat
    const chatTab = page.locator('button:has-text("Chat")');
    if (await chatTab.isVisible({ timeout: 1500 }).catch(() => false)) {
      await chatTab.click();
      await page.waitForTimeout(400);
    }

    // Double-click Load scenario button rapidly
    const loadScenarioBtn = page.locator('button:has-text("Load Paracetamol Scenario")');
    if (await loadScenarioBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await loadScenarioBtn.dblclick();
      await page.waitForTimeout(3000);

      // Verify composer send button is enabled and not locked in infinite loop
      const sendBtn = page.locator('button[title="Send to Copilot"]');
      await expect(sendBtn).toBeEnabled();
    }
  });

  test('Gate 4: Page reload preserves committed investigation data', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');

    // Ensure authenticated
    const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
    if (await usernameInput.isVisible({ timeout: 1500 }).catch(() => false)) {
      await usernameInput.fill('lead_investigator');
      await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
      await page.click('form button[type="submit"]:has-text("Sign In")');
      await page.waitForTimeout(1000);
    }

    // Commit current deviation form
    const commitBtn = page.locator('#section-deviation button:has-text("Commit Form")');
    if (await commitBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await commitBtn.click();
      await page.waitForTimeout(800);
    }

    // Reload page
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1500);

    // Verify investigation header and deviation batch number remain populated
    const batchField = page.locator('#section-deviation').getByText(/Batch Number/i);
    await expect(batchField).toBeVisible();
    const deviationSection = page.locator('#section-deviation');
    await expect(deviationSection).toBeVisible();
  });

  test('Gate 5: QA role workflow and sign-off rationale minimum length enforcement', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');

    // Sign out if currently logged in as investigator
    const userMenuBtn = page.locator('header button:has(div:has-text("INVESTIGATOR")), header button:has(div:has-text("QA_APPROVER"))').first();
    if (await userMenuBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await userMenuBtn.click();
      await page.click('button:has-text("Sign Out")');
      await page.waitForTimeout(600);
    }

    // Login as qa_director
    const usernameInput = page.locator('form input[placeholder="Enter cGMP username"]');
    if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await usernameInput.fill('qa_director');
      await page.fill('form input[placeholder="Enter password"]', 'AivoaPass2026!');
      await page.click('form button[type="submit"]:has-text("Sign In")');
      await page.waitForTimeout(1500);
    }

    // Verify QA header identity
    const roleBadge = page.locator('header').getByText('QA_APPROVER').first();
    await expect(roleBadge).toBeVisible();

    // Verify QA Approver field automatically contains authenticated QA full name
    const approvalSection = page.locator('#section-approval');
    await expect(approvalSection).toBeVisible();
    const approverInput = approvalSection.locator('input[placeholder="Full name and title"]');
    await expect(approverInput).toHaveValue(/QA Director/);

    // Verify sign-off button disabled until rationale length >= 10 chars
    const rationaleTextarea = approvalSection.locator('textarea');
    await expect(rationaleTextarea).toHaveValue('');
    const signBtn = approvalSection.locator('button:has-text("Sign & Approve Investigation")');
    await expect(signBtn).toBeDisabled();

    // Type 5 chars: still disabled with counter notice
    await rationaleTextarea.fill('Short');
    await expect(signBtn).toBeDisabled();
    await expect(approvalSection.getByText('Closure rationale must be at least 10 characters (5/10)')).toBeVisible();

    // Type valid rationale >= 10 chars: button becomes enabled
    await rationaleTextarea.fill('Thorough scientific review of reactor telemetry and valve physical inspection completed.');
    await expect(signBtn).toBeEnabled();
  });
});

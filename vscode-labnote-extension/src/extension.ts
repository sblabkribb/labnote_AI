import * as vscode from 'vscode';

const fetch = require('node-fetch');

// API 응답 타입 정의
interface LabNoteResponse { response: string; }
interface ChatResponse { response: string; conversation_id: string; }
interface PopulateResponse { uo_id: string; section: string; options: string[]; }

// QuickPick 아이템 타입
interface UnitOperationQuickPickItem extends vscode.QuickPickItem { id: string; }
// findSectionContext 함수의 반환 타입을 명확하게 인터페이스로 정의합니다.
interface SectionContext {
    uoId: string;
    section: string;
    query: string;
    fileContent: string;
    placeholderRange: vscode.Range;
}

// 상수
const ALL_WORKFLOWS: { [id: string]: string } = {
    "WD010": "General Design of Experiment", "WD020": "Adaptive Laboratory Evolution Design", "WD030": "Growth Media Design", "WD040": "Parallel Cell Culture/Fermentation Design", "WD050": "DNA Oligomer Pool Design", "WD060": "Genetic Circuit Design", "WD070": "Vector Design", "WD080": "Artificial Genome Design", "WD090": "Genome Editing Design", "WD100": "Protein Library Design", "WD110": "De novo Protein/Enzyme Design", "WD120": "Retrosynthetic Pathway Design", "WD130": "Pathway Library Design",
    "WB005": "Nucleotide Quantification", "WB010": "DNA Oligomer Assembly", "WB020": "DNA Library Construction", "WB025": "Sequencing Library Preparation", "WB030": "DNA Assembly", "WB040": "DNA Purification", "WB045": "DNA Extraction", "WB050": "RNA Extraction", "WB060": "DNA Multiplexing", "WB070": "Cell-free Mixture Preparation", "WB080": "Cell-free Protein/Enzyme Expression", "WB090": "Protein Purification", "WB100": "Growth Media Preparation and Sterilization", "WB110": "Competent Cell Construction", "WB120": "Biology-mediated DNA Transfers", "WB125": "Colony Picking", "WB130": "Solid Media Cell Culture", "WB140": "Liquid Media Cell Culture", "WB150": "PCR-based Target Amplification",
    "WT010": "Nucleotide Sequencing", "WT012": "Targeted mRNA Expression Measurement", "WT015": "Nucleic Acid Size Verification", "WT020": "Protein Expression Measurement", "WT030": "Protein/Enzyme Activity Measurement", "WT040": "Parallel Cell-free Protein/Enzyme Reaction", "WT045": "Mammalian Cell Cytotoxicity Assay", "WT046": "Microbial Viability and Cytotoxicity Assay", "WT050": "Sample Pretreatment", "WT060": "Metabolite Measurement", "WT070": "High-throughput Single Metabolite Measurement", "WT080": "Image Analysis", "WT085": "Mycoplasma Contamination Test", "WT090": "High-speed Cell Sorting", "WT100": "Micro-scale Parallel Cell Culture", "WT110": "Micro-scale Parallel Cell Fermentation", "WT120": "Parallel Cell Fermentation", "WT130": "Parallel Mammalian Cell Fermentation", "WT140": "Lab-scale Fermentation", "WT150": "Pilot-scale Fermentation", "WT160": "Industrial-scale Fermentation",
    "WL010": "Sequence Variant Analysis", "WL020": "Genome Resequencing Analysis", "WL030": "De novo Genome Analysis", "WL040": "Metagenomic Analysis", "WL050": "Transcriptome Analysis", "WL055": "Single Cell Analysis", "WL060": "Metabolic Pathway Optimization Model Development", "WL070": "Phenotypic Data Analysis", "WL080": "Protein/Enzyme Optimization Model Development", "WL090": "Fermentation Optimization Model Development", "WL100": "Foundation Model Development"
};
const ALL_UOS: { [id: string]: string } = {
    "UHW010": "Liquid Handling", "UHW015": "Bulk Liquid Dispenser", "UHW020": "96 Channel Liquid Handling", "UHW030": "Nanoliter Liquid Dispensing", "UHW040": "Desktop Liquid Handling", "UHW050": "Single Cell Sequencing Preparation", "UHW060": "Colony Picking", "UHW070": "Cell Sorting", "UHW080": "Cell Lysis", "UHW090": "Electroporation", "UHW100": "Thermocycling", "UHW110": "Real-time PCR", "UHW120": "Plate Handling", "UHW130": "Sealing", "UHW140": "Peeling", "UHW150": "Capping Decapping", "UHW160": "Sample Storage", "UHW170": "Plate Storage", "UHW180": "Incubation", "UHW190": "HT Aerobic Fermentation", "UHW200": "HT Anaerobic Fermentation", "UHW210": "Microbioreactor Fermentation", "UHW220": "Bioreactor Fermentation", "UHW230": "Nucleic Acid Fragment Analysis", "UHW240": "Protein Fragment Analysis", "UHW250": "Nucleic Acid Purification", "UHW255": "Centrifuge", "UHW260": "Short-read Sequence Analysis", "UHW265": "Sanger Sequencing", "UHW270": "Long-read Sequence Analysis", "UHW280": "Sequence Quality Control", "UHW290": "LC-MS-MS", "UHW300": "LC-MS", "UHW310": "HPLC", "UHW320": "UPLC", "UHW330": "GC", "UHW340": "GC-MS", "UHW350": "GC-MS-MS", "UHW355": "SPE-MS-MS", "UHW360": "FPLC", "UHW365": "Rapid Sugar Analyzer", "UHW370": "Oligomer Synthesis", "UHW380": "Microplate Reading", "UHW390": "Microscopy Imaging", "UHW400": "Manual",
    "USW005": "Biological Database", "USW010": "DNA Oligomer Pool Design", "USW020": "Primer Design", "USW030": "Vector Design", "USW040": "Sequence Optimization", "USW050": "Synthesis Screening", "USW060": "Structure-based Sequence Generation", "USW070": "Protein Structure Prediction", "USW080": "Protein Structure Generation", "USW090": "Retrosynthetic Pathway Design", "USW100": "Enzyme Identification", "USW110": "Sequence Alignment", "USW120": "Sequence Trimming and Filtering", "USW130": "Read Mapping and Alignment", "USW140": "Sequence Assembly", "USW145": "Metagenomic Assembly", "USW150": "Sequence Quality Control", "USW160": "Demultiplexing", "USW170": "Variant Calling", "USW180": "RNA-Seq Analysis", "USW185": "Gene Set Enrichment Analysis", "USW190": "Proteomics Data Analysis", "USW200": "Phylogenetic Analysis", "USW210": "Metabolic Flux Analysis", "USW220": "Deep Learning Data Preparation", "USW230": "Sequence Embedding", "USW240": "Deep Learning Model Training", "USW250": "Model Evaluation", "USW260": "Hyperparameter Tuning", "USW270": "Model Deployment", "USW280": "Monitoring and Reporting", "USW290": "Phenotype Data Preprocessing", "USW300": "XCMS Analysis", "USW310": "Flow Cytometry Analysis", "USW320": "DNA Assembly Simulation", "USW325": "Gene Editing Simulation", "USW330": "Well Plate Mapping", "USW340": "Computation"
};


export function activate(context: vscode.ExtensionContext) {
    console.log("--- LabNote AI Extension v0.7 (Robust Context Finder) ACTIVATED ---");
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

    const outputChannel = vscode.window.createOutputChannel("LabNote AI");
    outputChannel.appendLine("LabNote AI extension is now active.");
    // 1. 연구노트 뼈대 생성 명령어
    const generateDisposable = vscode.commands.registerCommand('labnote.ai.generate', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: '생성할 연구노트의 핵심 내용을 입력하세요.',
            placeHolder: '예: Golden Gate Assembly 이용한 플라스미드 제작'
        });
        if (userInput) await interactiveGenerateFlow(userInput, outputChannel);
    });
    // 2. 섹션별 내용 채우기 명령어 (populateSectionFlow에 메인 `context`를 전달)
    const populateDisposable = vscode.commands.registerCommand('labnote.ai.populateSection', async () => {
        await populateSectionFlow(context, outputChannel);
    });

    const chatDisposable = vscode.commands.registerCommand('labnote.ai.chat', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: 'AI에게 질문할 내용을 입력하세요.',
            placeHolder: '예: CRISPR-Cas9 시스템에 대해 설명해줘'
        });
        if (userInput) await callChatApi(userInput, outputChannel);
    });

    context.subscriptions.push(generateDisposable, populateDisposable, chatDisposable);
}

// --- 주요 기능 구현부 ---

async function populateSectionFlow(extensionContext: vscode.ExtensionContext, outputChannel: vscode.OutputChannel) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage("활성화된 에디터가 없습니다.");
        return;
    }

    try {
        // 1. 현재 커서 위치에서 컨텍스트(UO, 섹션, 주제) 파싱
        const sectionContext = findSectionContext(editor.document, editor.selection.active);
        if (!sectionContext) {
            vscode.window.showErrorMessage("현재 커서가 위치한 곳에서 채울 수 있는 Unit Operation 섹션(과 플레이스홀더)을 찾을 수 없습니다.");
            return;
        }

        const { uoId, section, query, fileContent, placeholderRange } = sectionContext;
        outputChannel.appendLine(`[Action] Populate section request for UO '${uoId}', Section '${section}'`);
        // 2. 프로그레스 바 표시 및 API 호출
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `LabNote AI: '${section}' 섹션 생성 중...`,
            cancellable: true
        }, async (progress, token) => {
            progress.report({ increment: 20, message: "AI 에이전트 팀 호출 중..." });

            const config = vscode.workspace.getConfiguration('labnote.ai');
            const baseUrl = config.get<string>('backendUrl');
            if (!baseUrl) throw new Error("Backend URL이 설정되지 않았습니다.");

            const populateResponse = await fetch(`${baseUrl}/populate_note`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_content: fileContent, uo_id: uoId, section, query })
            });

            if (!populateResponse.ok) {
                throw new Error(`AI 초안 생성 실패 (HTTP ${populateResponse.status}): ${await populateResponse.text()}`);
            }
            const populateData = await populateResponse.json() as PopulateResponse;
            if (!populateData.options || populateData.options.length === 0) {
                vscode.window.showInformationMessage("AI가 생성한 초안이 없습니다.");
                return;
            }

            const panel = createPopulateWebviewPanel(section, populateData.options);

            panel.webview.onDidReceiveMessage(
                async message => {
                    if (message.command === 'applyOption') {
                        const chosenIndex = parseInt(message.index, 10);
                        if (isNaN(chosenIndex) || chosenIndex < 0 || chosenIndex >= populateData.options.length) {
                            vscode.window.showErrorMessage("잘못된 선택입니다.");
                            return;
                        }

                        const chosenTextWithAttribution = populateData.options[chosenIndex];
                        // ✨ 수정된 부분: 참고 SOP 정보 제거
                        const chosenText = chosenTextWithAttribution.replace(/\[참고 SOP:.*?\]\s*\n\n/, '');
                        const rejectedOptions = populateData.options.filter((_, index) => index !== chosenIndex);

                        await editor.edit(editBuilder => {
                            editBuilder.replace(placeholderRange, chosenText);
                        });
                        
                        fetch(`${baseUrl}/record_preference`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                uo_id: uoId, 
                                section, 
                                chosen: chosenText, // Attribution이 제거된 텍스트로 기록
                                rejected: rejectedOptions, 
                                query,
                                file_content: editor.document.getText()
                            })
                        }).catch((err: any) => {
                            outputChannel.appendLine(`[WARN] DPO 데이터 기록 실패: ${err.message}`);
                        });

                        vscode.window.showInformationMessage(`'${section}' 섹션이 업데이트되었습니다.`);
                        panel.dispose();
                    }
                },
                undefined,
                extensionContext.subscriptions
            );
        });
    } catch (error: any) {
        vscode.window.showErrorMessage(`LabNote AI 작업 중 오류 발생: ${error.message}`);
        outputChannel.appendLine(`[ERROR] ${error.message}`);
        outputChannel.show(true);
    }
}

function createPopulateWebviewPanel(section: string, options: string[]): vscode.WebviewPanel {
    const panel = vscode.window.createWebviewPanel(
        'labnoteAiPopulate', `AI 제안: ${section}`, vscode.ViewColumn.Beside,
        { enableScripts: true, localResourceRoots: [] }
    );
    panel.webview.html = getWebviewContent(section, options);
    return panel;
}
// --- Webview HTML 내용 생성 함수 ---
function getWebviewContent(section: string, options: string[]): string {
    const optionCards = options.map((option, index) => {
        const optionTitles = ["간결한 버전 📜", "상세한 버전 🔬", "대안/고려사항 🤔"];
        const title = optionTitles[index] || `옵션 ${index + 1}`;
        const escapedOption = option.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        return `<div class="option-card" data-index="${index}"><h3>${title}</h3><pre><code>${escapedOption}</code></pre></div>`;
    }).join('');

    return `<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 제안: ${section}</title>
        <style>
            body { font-family: sans-serif; padding: 1em; }
            .option-card { border: 1px solid #555; border-radius: 5px; padding: 1em; margin-bottom: 1em; cursor: pointer; transition: all 0.2s ease-in-out; }
            .option-card:hover { border-color: #007acc; transform: translateY(-2px); }
            .option-card.selected { border: 2px solid #007acc; box-shadow: 0 0 8px #007acc66; }
            pre { white-space: pre-wrap; word-wrap: break-word; background-color: #2e2e2e; padding: 10px; border-radius: 4px; }
            button { padding: 10px 15px; border: none; background-color: #007acc; color: white; border-radius: 5px; cursor: pointer; font-size: 1em; width: 100%; margin-top: 1em; }
            button:hover { background-color: #005a99; }
            button:disabled { background-color: #555; cursor: not-allowed; }
        </style>
    </head>
    <body>
        <h1>"${section}" 섹션에 대한 AI 제안</h1>
        <p>삽입할 내용을 선택하고 '선택 항목 적용' 버튼을 클릭하세요.</p>
        <div id="options-container">${optionCards}</div>
        <button id="apply-btn" disabled>선택 항목 적용</button>
        <script>
            const vscode = acquireVsCodeApi();
            const cards = document.querySelectorAll('.option-card');
            const applyBtn = document.getElementById('apply-btn');
            let selectedCard = null;
            cards.forEach(card => {
                card.addEventListener('click', () => {
                    cards.forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedCard = card;
                    applyBtn.disabled = false;
                });
            });
            applyBtn.addEventListener('click', () => {
                if (!selectedCard) return;
                vscode.postMessage({ command: 'applyOption', index: selectedCard.dataset.index });
            });
        </script>
    </body>
    </html>`;
}

/**
 * ✨ [개선된 로직]
 * 현재 커서 위치를 기반으로 상위의 섹션(####)과 Unit Operation(###)을 찾고,
 * 그 섹션 내에 교체할 플레이스홀더 라인이 있는지 다시 탐색하여 컨텍스트를 확정합니다.
 * 이를 통해 사용자는 섹션 내 아무 곳에나 커서를 두고 명령을 실행할 수 있습니다.
 */
function findSectionContext(document: vscode.TextDocument, position: vscode.Position): SectionContext | null {
    let currentSection = "";
    let currentUoId = "";
    let sectionLineNum = -1;

    // 1. 현재 커서 위치에서 위로 올라가며 가장 가까운 '섹션' 헤더(####)를 찾습니다.
    for (let i = position.line; i >= 0; i--) {
        const lineText = document.lineAt(i).text;
        const sectionMatch = lineText.match(/^####\s*([A-Za-z\s&]+)/);
        if (sectionMatch) {
            currentSection = sectionMatch[1].trim();
            sectionLineNum = i;
            break;
        }
    }
    if (!currentSection) return null; // 문서에서 섹션을 찾지 못함

    // 2. 찾은 섹션 위치에서 다시 위로 올라가며 가장 가까운 'Unit Operation' 헤더(###)를 찾습니다.
    for (let i = sectionLineNum - 1; i >= 0; i--) {
        const lineText = document.lineAt(i).text;
        const uoMatch = lineText.match(/^###\s*\[(U[A-Z]{2,3}\d{3})/);
        if (uoMatch) {
            currentUoId = uoMatch[1];
            break;
        }
    }
    if (!currentUoId) return null; // 섹션에 대한 UO를 찾지 못함

    // 3. 찾은 섹션 내부를 탐색하여 교체할 '플레이스홀더' 라인을 찾습니다.
    const placeholderRegex = /^\s*(-\s*)?\(.*\)\s*$/;
    let placeholderRange: vscode.Range | null = null;
    
    // 섹션 시작 다음 줄부터 탐색 시작
    for (let i = sectionLineNum + 1; i < document.lineCount; i++) {
        const line = document.lineAt(i);
        // 다른 헤더(### 또는 ####)를 만나면 현재 섹션이 끝난 것이므로 탐색 중지
        if (line.text.startsWith('###') || line.text.startsWith('####')) {
            break;
        }
        if (placeholderRegex.test(line.text)) {
            placeholderRange = line.range;
            break; // 첫 번째로 발견된 플레이스홀더를 대상으로 함
        }
    }
    
    if (!placeholderRange) return null; // 현재 섹션 내에 채울 플레이스홀더가 없음

    // 4. YAML frontmatter에서 title(query)을 찾습니다.
    const text = document.getText();
    const yamlMatch = text.match(/^---\s*[\r\n]+title:\s*["']?(.*?)["']?[\r\n]+/);
    const query = yamlMatch ? yamlMatch[1].replace(/\[AI Generated\]\s*/, '').trim() : "Untitled Experiment";

    return { uoId: currentUoId, section: currentSection, query, fileContent: text, placeholderRange };
}


// interactiveGenerateFlow, showWorkflowSelectionMenu, showUnifiedUoSelectionMenu, callChatApi 함수는 기존과 동일합니다.
async function interactiveGenerateFlow(userInput: string, outputChannel: vscode.OutputChannel) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "LabNote AI 분석 중...",
        cancellable: true
    }, async (progress, token) => {
        try {
            progress.report({ increment: 10, message: "실험 구조를 분석하고 추천받는 중..." });
            const config = vscode.workspace.getConfiguration('labnote.ai');
            const baseUrl = config.get<string>('backendUrl');
            if (!baseUrl) throw new Error("Backend URL이 설정되지 않았습니다.");

            const finalWorkflowId = await showWorkflowSelectionMenu();
            if (!finalWorkflowId) { return; }
            outputChannel.appendLine(`[User Action] 최종 선택된 WF: ${finalWorkflowId}`);

            const finalUoIds = await showUnifiedUoSelectionMenu([]);
            if (finalUoIds === undefined || finalUoIds.length === 0) { return; }
            outputChannel.appendLine(`[User Action] 최종 선택된 UOs: ${finalUoIds.join(', ')}`);
            
            progress.report({ increment: 60, message: "연구노트 뼈대 생성 중..." });

            const createScaffoldResponse = await fetch(`${baseUrl}/create_scaffold`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userInput, workflow_id: finalWorkflowId, unit_operation_ids: finalUoIds, experimenter: "AI Assistant" }),
                timeout: 300000
            });
            if (!createScaffoldResponse.ok) throw new Error(`뼈대 생성 실패 (HTTP ${createScaffoldResponse.status}): ${await createScaffoldResponse.text()}`);
            
            const scaffoldData = await createScaffoldResponse.json() as LabNoteResponse;

            progress.report({ increment: 90, message: "결과 표시 중..." });
            const doc = await vscode.workspace.openTextDocument({ content: scaffoldData.response, language: 'markdown' });
            await vscode.window.showTextDocument(doc, { preview: false });

            outputChannel.appendLine(`[Success] 랩노트 생성이 완료되었습니다.`);
            outputChannel.show(true);

        } catch (error: any) {
            vscode.window.showErrorMessage('LabNote AI 작업 중 오류가 발생했습니다. 자세한 내용은 출력 채널을 확인하세요.');
            outputChannel.appendLine(`[ERROR] ${error.message}`);
            outputChannel.show(true);
        }
    });
}

async function showWorkflowSelectionMenu(): Promise<string | undefined> {
    const allWorkflowItems = Object.keys(ALL_WORKFLOWS).map(id => ({ id: id, label: `[${id}]`, description: ALL_WORKFLOWS[id] }));
    const selectedItem = await vscode.window.showQuickPick(allWorkflowItems, { title: '사용할 워크플로우(Workflow) 선택', matchOnDescription: true, placeHolder: '이름이나 ID로 검색...' });
    return selectedItem?.id;
}

async function showUnifiedUoSelectionMenu(recommendedIds: string[]): Promise<string[] | undefined> {
    const recommendedSet = new Set(recommendedIds);
    const allUoItems: UnitOperationQuickPickItem[] = Object.keys(ALL_UOS).map(id => ({ id: id, label: `[${id}]`, description: ALL_UOS[id], picked: recommendedSet.has(id) }));
    allUoItems.sort((a, b) => {
        const aIsRecommended = recommendedSet.has(a.id);
        const bIsRecommended = recommendedSet.has(b.id);
        if (aIsRecommended && !bIsRecommended) return -1;
        if (!aIsRecommended && bIsRecommended) return 1;
        if (!aIsRecommended && !bIsRecommended) { return a.id.localeCompare(b.id); }
        return 0;
    });
    const selectedItems = await vscode.window.showQuickPick(allUoItems, { title: '사용할 Unit Operation 선택 (AI 추천 항목이 미리 선택됨)', canPickMany: true, matchOnDescription: true, placeHolder: '이름이나 ID로 검색하여 선택/해제 후 Enter', });
    return selectedItems?.map(item => item.id);
}


async function callChatApi(userInput: string, outputChannel: vscode.OutputChannel) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "LabNote AI가 응답 중입니다...",
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 20, message: "AI에게 질문하는 중..." });
            const config = vscode.workspace.getConfiguration('labnote.ai');
            const baseUrl = config.get<string>('backendUrl');
            if (!baseUrl) throw new Error("Backend URL이 설정되지 않았습니다.");
            
            const response = await fetch(`${baseUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userInput }),
                timeout: 180000
            });

            if (!response.ok) {
                const errorBody = await response.text();
                throw new Error(`채팅 실패 (HTTP ${response.status}): ${errorBody}`);
            }
            const chatData = await response.json() as ChatResponse;

            const doc = await vscode.workspace.openTextDocument({
                content: `# AI 답변: ${userInput}\n\n---\n\n${chatData.response}`,
                language: 'markdown'
            });
            await vscode.window.showTextDocument(doc, { preview: false });

        } catch (error: any) {
            vscode.window.showErrorMessage('LabNote AI와 대화 중 오류가 발생했습니다.');
            outputChannel.appendLine(`[ERROR] ${error.message}`);
            outputChannel.show(true);
        }
    });
}

export function deactivate() {}
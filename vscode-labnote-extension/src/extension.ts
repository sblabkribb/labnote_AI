import * as vscode from 'vscode';

const fetch = require('node-fetch');

// API 응답 타입 정의
interface StructureResponse {
    recommended_workflow_id: string;
    recommended_unit_operation_ids: string[];
    sources?: string[];
}
interface LabNoteResponse { response: string; sources?: string[]; }
interface ChatResponse { response: string; conversation_id: string; }
interface UnitOperationQuickPickItem extends vscode.QuickPickItem { id: string; }

// 전체 워크플로우 및 유닛 오퍼레이션 목록
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
    console.log("--- LabNote AI Extension v8.0 (Fully Interactive UI) ACTIVATED ---");
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

    const outputChannel = vscode.window.createOutputChannel("LabNote AI");
    outputChannel.appendLine('LabNote AI extension is now active.');

    const generateDisposable = vscode.commands.registerCommand('labnote.ai.generate', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: '생성할 연구노트의 핵심 내용을 입력하세요.',
            placeHolder: '예: Golden Gate Assembly 이용한 플라스미드 제작'
        });
        if (userInput) await interactiveGenerateFlow(userInput, outputChannel);
    });

    const chatDisposable = vscode.commands.registerCommand('labnote.ai.chat', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: 'AI에게 질문할 내용을 입력하세요.',
            placeHolder: '예: CRISPR-Cas9 시스템에 대해 설명해줘'
        });
        if (userInput) await callChatApi(userInput, outputChannel);
    });

    context.subscriptions.push(generateDisposable, chatDisposable);
}

async function interactiveGenerateFlow(userInput: string, outputChannel: vscode.OutputChannel) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "LabNote AI 분석 중...",
        cancellable: true
    }, async (progress, token) => {
        try {
            // --- 1단계: 구조 추천 (AI 추천 + 사용자 선택) ---
            progress.report({ increment: 10, message: "실험 구조를 분석하고 추천받는 중..." });
            const config = vscode.workspace.getConfiguration('labnote.ai');
            const baseUrl = config.get<string>('backendUrl');
            if (!baseUrl) throw new Error("Backend URL이 설정되지 않았습니다.");

            // AI에게 추천을 받지만, 이 단계에서 API를 호출하지 않고 사용자에게 바로 선택권을 줌
            // 필요 시, 이전처럼 /recommend_structure를 호출하여 recommendedIds를 채울 수 있음
            
            // 워크플로우 선택
            const finalWorkflowId = await showWorkflowSelectionMenu();
            if (!finalWorkflowId) {
                vscode.window.showInformationMessage("작업이 취소되었습니다.");
                return;
            }
            outputChannel.appendLine(`[User Action] 최종 선택된 WF: ${finalWorkflowId}`);

            // 유닛 오퍼레이션 선택
            const finalUoIds = await showUnifiedUoSelectionMenu([]); // 빈 추천 목록으로 시작
            if (finalUoIds === undefined || finalUoIds.length === 0) {
                vscode.window.showInformationMessage("작업이 취소되었거나 Unit Operation이 선택되지 않았습니다.");
                return;
            }
            outputChannel.appendLine(`[User Action] 최종 선택된 UOs: ${finalUoIds.join(', ')}`);
            
            // --- 2단계: 최종 내용 생성 요청 ---
            progress.report({ increment: 60, message: "선택된 구조로 최종 랩노트 생성 중..." });

            const createNoteResponse = await fetch(`${baseUrl}/create_filled_note`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: userInput,
                    workflow_id: finalWorkflowId,
                    unit_operation_ids: finalUoIds,
                    experimenter: "AI Assistant"
                }),
                timeout: 300000
            });
            if (!createNoteResponse.ok) throw new Error(`최종 노트 생성 실패 (HTTP ${createNoteResponse.status}): ${await createNoteResponse.text()}`);
            
            const finalNoteData = await createNoteResponse.json() as LabNoteResponse;

            // --- 3단계: 결과 표시 ---
            progress.report({ increment: 90, message: "결과 표시 중..." });
            const doc = await vscode.workspace.openTextDocument({
                content: `# 연구노트 초안: ${userInput}\n\n---\n\n${finalNoteData.response}`,
                language: 'markdown'
            });
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

/**
 * [신규 v8.0] 전체 워크플로우 목록에서 사용자가 직접 검색하고 선택하게 하는 함수
 */
async function showWorkflowSelectionMenu(): Promise<string | undefined> {
    const allWorkflowItems = Object.keys(ALL_WORKFLOWS).map(id => ({
        id: id,
        label: `[${id}]`,
        description: ALL_WORKFLOWS[id]
    }));

    const selectedItem = await vscode.window.showQuickPick(allWorkflowItems, {
        title: '사용할 워크플로우(Workflow) 선택',
        matchOnDescription: true,
        placeHolder: '이름이나 ID로 검색...'
    });

    return selectedItem?.id;
}


/**
 * [개선된 v8.0] AI 추천과 전체 목록을 통합하여 보여주는 유닛 오퍼레이션 선택 메뉴
 */
async function showUnifiedUoSelectionMenu(recommendedIds: string[]): Promise<string[] | undefined> {
    const recommendedSet = new Set(recommendedIds);

    const allUoItems: UnitOperationQuickPickItem[] = Object.keys(ALL_UOS).map(id => ({
        id: id,
        label: `[${id}]`,
        description: ALL_UOS[id],
        picked: recommendedSet.has(id) 
    }));

    allUoItems.sort((a, b) => {
        const aIsRecommended = recommendedSet.has(a.id);
        const bIsRecommended = recommendedSet.has(b.id);
        if (aIsRecommended && !bIsRecommended) return -1;
        if (!aIsRecommended && bIsRecommended) return 1;
        // 추천되지 않은 항목들은 ID순으로 정렬
        if (!aIsRecommended && !bIsRecommended) {
            return a.id.localeCompare(b.id);
        }
        return 0;
    });

    const selectedItems = await vscode.window.showQuickPick(allUoItems, {
        title: '사용할 Unit Operation 선택 (AI 추천 항목이 미리 선택됨)',
        canPickMany: true,
        matchOnDescription: true,
        placeHolder: '이름이나 ID로 검색하여 선택/해제 후 Enter',
    });

    return selectedItems?.map(item => item.id);
}


// 일반 대화 함수 (기존과 동일)
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
import * as vscode from 'vscode';

// node-fetch v2는 CommonJS 모듈이므로 require 구문을 사용하는 것이 가장 안정적입니다.
const fetch = require('node-fetch');

// --- API 응답 타입 정의 ---
interface StructureResponse {
    recommended_workflow_id: string;
    recommended_unit_operation_ids: string[];
    sources?: string[];
}

interface LabNoteResponse {
    response: string;
    sources?: string[];
}

interface ChatResponse {
    response: string;
    conversation_id: string;
}

// [신규] 유닛 오퍼레이션 선택을 위한 Quick Pick 아이템
interface UnitOperationQuickPickItem extends vscode.QuickPickItem {
    id: string; // 예: "UHW010"
}


export function activate(context: vscode.ExtensionContext) {
    
    console.log("--- LabNote AI Extension v5.0 (Interactive Workflow) ACTIVATED ---");

    // VESSL의 만료된 인증서 문제를 해결하기 위한 전역 설정
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

    const outputChannel = vscode.window.createOutputChannel("LabNote AI");
    outputChannel.appendLine('LabNote AI extension is now active.');

    // --- 1. 연구노트 생성 명령어 (대화형으로 완전히 변경됨) ---
    const generateDisposable = vscode.commands.registerCommand('labnote.ai.generate', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: '생성할 연구노트의 핵심 내용을 입력하세요.',
            placeHolder: '예: Golden Gate Assembly 이용한 플라스미드 제작'
        });

        if (!userInput) return;

        // 2단계 워크플로우 실행
        await interactiveGenerateFlow(userInput, outputChannel);
    });

    // --- 2. 일반 대화 명령어 (기존과 거의 동일, conversation_id 관리 추가) ---
    const chatDisposable = vscode.commands.registerCommand('labnote.ai.chat', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: 'AI에게 질문할 내용을 입력하세요.',
            placeHolder: '예: CRISPR-Cas9 시스템에 대해 설명해줘'
        });

        if (!userInput) return;
        
        // 간단한 챗 API 호출
        await callChatApi(userInput, outputChannel);
    });

    context.subscriptions.push(generateDisposable, chatDisposable);
}

/**
 * [신규] 연구노트 생성을 위한 대화형 워크플로우
 */
async function interactiveGenerateFlow(userInput: string, outputChannel: vscode.OutputChannel) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "LabNote AI 분석 중...",
        cancellable: true
    }, async (progress, token) => {
        try {
            // --- 1단계: 구조 추천 요청 ---
            progress.report({ increment: 10, message: "실험 구조를 분석하고 추천받는 중..." });
            outputChannel.appendLine(`[Request] 구조 추천 요청: "${userInput}"`);

            const config = vscode.workspace.getConfiguration('labnote.ai');
            const baseUrl = config.get<string>('backendUrl');
            if (!baseUrl) throw new Error("Backend URL이 설정되지 않았습니다.");

            const structureResponse = await fetch(`${baseUrl}/recommend_structure`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userInput }),
                timeout: 120000 // 2분
            });

            if (!structureResponse.ok) {
                const errorBody = await structureResponse.text();
                throw new Error(`구조 추천 실패 (HTTP ${structureResponse.status}): ${errorBody}`);
            }
            const structureData = await structureResponse.json() as StructureResponse;
            outputChannel.appendLine(`[Response] 추천 WF: ${structureData.recommended_workflow_id}, 추천 UOs: ${structureData.recommended_unit_operation_ids.join(', ')}`);

            if (token.isCancellationRequested) return;

            // --- 2단계: 사용자에게 유닛 오퍼레이션 선택/확인 받기 ---
            progress.report({ increment: 40, message: "사용자 확인 대기 중..." });
            
            const uoItems: UnitOperationQuickPickItem[] = structureData.recommended_unit_operation_ids.map(id => ({
                id: id,
                label: `[${id}]`, // 예: [UHW010]
                description: `(관련 유닛 오퍼레이션)`, // 필요 시 여기에 UO 이름을 추가할 수 있음
                picked: true // 기본적으로 모두 선택
            }));
            
            const selectedUoItems = await vscode.window.showQuickPick(uoItems, {
                title: '사용할 유닛 오퍼레이션을 선택하세요',
                canPickMany: true,
                placeHolder: '체크박스를 이용해 포함할 항목을 조정한 후 Enter를 누르세요.'
            });

            if (!selectedUoItems || selectedUoItems.length === 0) {
                vscode.window.showInformationMessage("작업이 취소되었습니다.");
                return;
            }
            const finalUoIds = selectedUoItems.map(item => item.id);
            outputChannel.appendLine(`[User Action] 최종 선택된 UOs: ${finalUoIds.join(', ')}`);

            // --- 3단계: 최종 내용 생성 요청 ---
            progress.report({ increment: 60, message: "선택된 구조로 최종 랩노트 생성 중..." });

            const createNoteResponse = await fetch(`${baseUrl}/create_filled_note`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: userInput,
                    workflow_id: structureData.recommended_workflow_id,
                    unit_operation_ids: finalUoIds,
                    experimenter: "AI Assistant" // 필요 시 이 부분도 사용자 입력을 받도록 수정 가능
                }),
                timeout: 300000 // 5분
            });

            if (!createNoteResponse.ok) {
                const errorBody = await createNoteResponse.text();
                throw new Error(`최종 노트 생성 실패 (HTTP ${createNoteResponse.status}): ${errorBody}`);
            }
            const finalNoteData = await createNoteResponse.json() as LabNoteResponse;

            // --- 4단계: 결과 표시 ---
            progress.report({ increment: 90, message: "결과 표시 중..." });
            const doc = await vscode.workspace.openTextDocument({
                content: `# 연구노트 초안: ${userInput}\n\n---\n\n${finalNoteData.response}`,
                language: 'markdown'
            });
            await vscode.window.showTextDocument(doc, { preview: false });

            outputChannel.appendLine(`[Success] 랩노트 생성이 완료되었습니다.`);
            if (structureData.sources && structureData.sources.length > 0) {
                outputChannel.appendLine(`[Info] 참고 자료: ${structureData.sources.join(', ')}`);
            }
            outputChannel.show(true);

        } catch (error: any) {
            vscode.window.showErrorMessage('LabNote AI 작업 중 오류가 발생했습니다. 자세한 내용은 출력 채널을 확인하세요.');
            outputChannel.appendLine(`[ERROR] ${error.message}`);
            outputChannel.show(true);
        }
    });
}

/**
 * 일반 대화를 처리하는 함수
 */
async function callChatApi(userInput: string, outputChannel: vscode.OutputChannel) {
    // conversation_id는 현재 구현에서는 상태를 유지하지 않음 (필요 시 context.workspaceState 등을 사용하여 저장 가능)
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
                body: JSON.stringify({ query: userInput }), // conversation_id는 생략
                timeout: 180000 // 3분
            });

            if (!response.ok) {
                const errorBody = await response.text();
                throw new Error(`채팅 실패 (HTTP ${response.status}): ${errorBody}`);
            }
            const chatData = await response.json() as ChatResponse;

            // 채팅 결과는 정보 메시지나 새 문서로 보여줄 수 있음. 여기서는 새 문서로 표시.
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
import * as vscode from 'vscode';
// node-fetch v2는 CommonJS 모듈이므로 require 구문을 사용하는 것이 가장 안정적입니다.
const fetch = require('node-fetch');

/**
 * @interface ApiResponse
 * @description API 응답 타입을 명확하게 정의하여 코드 안정성을 높입니다.
 */
interface ApiResponse {
    response: string;
    sources?: string[];
}

export function activate(context: vscode.ExtensionContext) {
    
    // 진단용 로그
    console.log("--- LabNote AI Extension v1.5 (Dual Mode) ACTIVATED ---");

    const outputChannel = vscode.window.createOutputChannel("LabNote AI");
    outputChannel.appendLine('LabNote AI extension is now active.');
    
    // --- [기존 기능] 연구노트 생성 ---
    let generateDisposable = vscode.commands.registerCommand('labnote.ai.generate', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: '생성할 연구노트의 내용을 입력하세요.',
            placeHolder: '예: DH5a Transformation 프로토콜 알려줘'
        });

        if (!userInput) return;
        
        // 백엔드 URL 설정 가져오기
        const config = vscode.workspace.getConfiguration('labnote.ai');
        const baseUrl = config.get<string>('backendUrl');
        if (!baseUrl) {
            vscode.window.showErrorMessage("LabNote AI 백엔드 URL이 설정되지 않았습니다.");
            return;
        }
        const apiUrl = `${baseUrl}/generate_labnote`;

        await callApi(userInput, apiUrl, outputChannel, true);
    });

    // --- [새로운 기능] 일반 대화 ---
    let chatDisposable = vscode.commands.registerCommand('labnote.ai.chat', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: 'AI에게 무엇이든 물어보세요.',
            placeHolder: '예: E.coli의 doubling time은 얼마야?'
        });

        if (!userInput) return;

        // 백엔드 URL 설정 가져오기
        const config = vscode.workspace.getConfiguration('labnote.ai');
        const baseUrl = config.get<string>('backendUrl');
        if (!baseUrl) {
            vscode.window.showErrorMessage("LabNote AI 백엔드 URL이 설정되지 않았습니다.");
            return;
        }
        const apiUrl = `${baseUrl}/chat`;

        await callApi(userInput, apiUrl, outputChannel, false);
    });

    context.subscriptions.push(generateDisposable, chatDisposable);
}

/**
 * API 호출 및 결과 처리를 위한 공통 함수
 * @param query 사용자 입력
 * @param apiUrl 호출할 API의 전체 URL
 * @param outputChannel 로그를 출력할 채널
 * @param isLabnote 랩노트 생성 여부 (결과 표시 방식 결정)
 */
async function callApi(query: string, apiUrl: string, outputChannel: vscode.OutputChannel, isLabnote: boolean) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "LabNote AI가 작동 중입니다...",
        cancellable: true
    }, async (progress, token) => {
        
        token.onCancellationRequested(() => {
            outputChannel.appendLine("사용자가 작업을 취소했습니다.");
        });

        progress.report({ increment: 10, message: "백엔드 서버에 요청을 보냅니다..." });
        outputChannel.appendLine(`[Request to ${apiUrl}] 사용자 쿼리: "${query}"`);

        // Node.js 환경 변수를 직접 조작하여 인증서 검증을 강제로 비활성화
        const originalRejectUnauthorized = process.env.NODE_TLS_REJECT_UNAUTHORIZED;
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
                timeout: 180000 // 타임아웃 3분
            });
            
            if (token.isCancellationRequested) return;
            progress.report({ increment: 40, message: "AI가 응답을 생성 중입니다..." });

            if (!response.ok) {
                const errorBody = await response.text();
                throw new Error(`HTTP Error: ${response.status} ${response.statusText}\n${errorBody}`);
            }

            const data = await response.json() as ApiResponse;

            if (token.isCancellationRequested) return;
            progress.report({ increment: 90, message: "결과를 표시합니다..." });

            // 결과 표시: 랩노트는 새 문서에, 일반 대화는 정보 메시지 창에 표시
            if (isLabnote) {
                const doc = await vscode.workspace.openTextDocument({
                    content: data.response,
                    language: 'markdown'
                });
                await vscode.window.showTextDocument(doc, { preview: false });
            } else {
                // 긴 답변도 잘 보이도록 모달 정보 창 사용
                await vscode.window.showInformationMessage("LabNote AI의 답변:", { modal: true, detail: data.response });
            }

            // 로그 및 참고 자료 출력
            if (data.sources && data.sources.length > 0) {
                outputChannel.appendLine(`[Response] 생성 완료. 참고 자료: ${data.sources.join(', ')}`);
            } else {
                outputChannel.appendLine(`[Response] 생성 완료.`);
            }
            outputChannel.show(true);

        } catch (error: any) {
            vscode.window.showErrorMessage('LabNote AI 생성 중 오류가 발생했습니다. 자세한 내용은 출력 채널을 확인하세요.');
            outputChannel.appendLine(`[ERROR] ${error.message}`);
            outputChannel.show(true);
        } finally {
            // 요청이 끝나면 환경 변수를 원래대로 복원
            process.env.NODE_TLS_REJECT_UNAUTHORIZED = originalRejectUnauthorized;
        }
    });
}

export function deactivate() {}

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
    
    // 진단용 로그: 확장 프로그램이 최신 코드로 실행되었는지 확인합니다.
    console.log("--- LabNote AI Extension v2.0 (Improved UX) ACTIVATED ---");

    // VESSL의 만료된 인증서 문제를 해결하기 위한 전역 설정입니다.
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

    const outputChannel = vscode.window.createOutputChannel("LabNote AI");
    outputChannel.appendLine('LabNote AI extension is now active.');

    // --- 1. 연구노트 생성 명령어 등록 ---
    const generateDisposable = vscode.commands.registerCommand('labnote.ai.generate', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: '생성할 연구노트의 내용을 입력하세요.',
            placeHolder: '예: Level 1 Golden Gate Assembly 프로토콜'
        });

        if (!userInput) return;

        // API 호출을 위한 공통 로직 실행
        await callApi(userInput, '/generate_labnote', outputChannel, "연구노트 초안");
    });

    // --- 2. 일반 대화 명령어 등록 ---
    const chatDisposable = vscode.commands.registerCommand('labnote.ai.chat', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: 'AI에게 질문할 내용을 입력하세요.',
            placeHolder: '예: CRISPR-Cas9 시스템에 대해 설명해줘'
        });

        if (!userInput) return;
        
        // API 호출을 위한 공통 로직 실행
        await callApi(userInput, '/chat', outputChannel, "AI 답변");
    });

    context.subscriptions.push(generateDisposable, chatDisposable);
}

/**
 * API 호출을 처리하고 결과를 새 문서에 표시하는 공통 함수
 * @param userInput 사용자가 입력한 텍스트
 * @param path API 경로 (e.g., '/generate_labnote' or '/chat')
 * @param outputChannel VS Code 출력 채널
 * @param resultType 결과 문서의 제목에 표시될 텍스트
 */
async function callApi(userInput: string, path: string, outputChannel: vscode.OutputChannel, resultType: string) {
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "LabNote AI가 작동 중입니다...",
        cancellable: true
    }, async (progress, token) => {
        
        token.onCancellationRequested(() => {
            outputChannel.appendLine("사용자가 작업을 취소했습니다.");
        });

        progress.report({ increment: 10, message: "백엔드 서버에 요청을 보냅니다..." });
        outputChannel.appendLine(`[Request] 사용자 쿼리: "${userInput}"`);

        try {
            // package.json의 설정에서 기본 URL을 읽어옵니다.
            const config = vscode.workspace.getConfiguration('labnote.ai');
            const baseUrl = config.get<string>('backendUrl');

            if (!baseUrl) {
                throw new Error("Backend URL이 설정되지 않았습니다. VS Code 설정을 확인해주세요.");
            }
            
            const fullUrl = `${baseUrl}${path}`;
            
            const response = await fetch(fullUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userInput }),
                timeout: 180000 // 타임아웃을 3분으로 넉넉하게 설정
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

            // --- 여기가 핵심 개선 사항 ---
            // 챗봇 결과도 이제 복사 및 편집이 가능한 새 문서 탭에 표시됩니다.
            const doc = await vscode.workspace.openTextDocument({
                content: `# ${resultType}: ${userInput}\n\n---\n\n${data.response}`,
                language: 'markdown'
            });
            await vscode.window.showTextDocument(doc, { preview: false });
            // -----------------------------

            if (data.sources && data.sources.length > 0) {
                outputChannel.appendLine(`[Response] 생성 완료. 참고 자료: ${data.sources.join(', ')}`);
            } else {
                outputChannel.appendLine(`[Response] 생성 완료.`);
            }
            outputChannel.show(true);

        } catch (error: any) {
            vscode.window.showErrorMessage('LabNote AI와 통신 중 오류가 발생했습니다. 자세한 내용은 출력 채널을 확인하세요.');
            outputChannel.appendLine(`[ERROR] ${error.message}`);
            outputChannel.show(true);
        }
    });
}

export function deactivate() {}
